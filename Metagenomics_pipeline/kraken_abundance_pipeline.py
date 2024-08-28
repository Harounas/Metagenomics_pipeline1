import os
from .trimmomatic import run_trimmomatic
from .bowtie2 import run_bowtie2
from .kraken2 import run_kraken2
import pandas as pd
from collections import defaultdict
import plotly.express as px
import random

def process_sample(forward, reverse, base_name, bowtie2_index, kraken_db, output_dir, threads):
    trimmed_forward, trimmed_reverse = run_trimmomatic(forward, reverse, base_name, output_dir, threads)
    unmapped_r1, unmapped_r2 = run_bowtie2(trimmed_forward, trimmed_reverse, base_name, bowtie2_index, output_dir, threads)
    kraken_report = run_kraken2(unmapped_r1, unmapped_r2, base_name, kraken_db, output_dir, threads)
    return kraken_report

def aggregate_kraken_results(kraken_dir, metadata_file, read_count, top_N, virus, bacteria):
    metadata = pd.read_csv(metadata_file, sep=",")
    sample_id_col = metadata.columns[0]  # Assume the first column is the sample ID

    # Dictionary to store aggregated results
    aggregated_results = {}

    # Iterate over each Kraken report file
    for file_name in os.listdir(kraken_dir):
        if file_name.endswith("_report.txt"):
            with open(os.path.join(kraken_dir, file_name), 'r') as f:
                for line in f:
                    fields = line.strip().split('\t')
                    perc_frag_cover = fields[0]
                    nr_frag_cover = fields[1]
                    nr_frag_direct_at_taxon = int(fields[2])
                    rank_code = fields[3]
                    ncbi_ID = fields[4]
                    scientific_name = fields[5]
                    parts = file_name.split('_')
                    extracted_part = '_'.join(parts[:-1])
                    sampleandtaxonid = extracted_part + str(ncbi_ID)

                    if rank_code == 'S' and nr_frag_direct_at_taxon >= read_count:
                        if extracted_part in metadata[sample_id_col].unique():
                            sample_metadata = metadata.loc[metadata[sample_id_col] == extracted_part].iloc[0].to_dict()
                            aggregated_results[sampleandtaxonid] = {
                                'Perc_frag_cover': perc_frag_cover,
                                'Nr_frag_cover': nr_frag_cover,
                                'Nr_frag_direct_at_taxon': nr_frag_direct_at_taxon,
                                'Rank_code': rank_code,
                                'NCBI_ID': ncbi_ID,
                                'Scientific_name': scientific_name,
                                'SampleID': extracted_part,
                                **sample_metadata
                            }

    # Output aggregated results to a TSV file
    merged_tsv_path = os.path.join(kraken_dir, "merged_kraken1.tsv")
    with open(merged_tsv_path, 'w') as f:
        # Write headers dynamically
        headers = ['Perc_frag_cover', 'Nr_frag_cover', 'Nr_frag_direct_at_taxon', 'Rank_code', 'NCBI_ID', 'Scientific_name', 'SampleID'] + metadata.columns[1:].tolist()
        f.write("\t".join(headers) + "\n")
        for sampleandtaxonid, data in aggregated_results.items():
            f.write("\t".join(str(data[col]) for col in headers) + "\n")

    return merged_tsv_path

def generate_abundance_plots(merged_tsv_path, virus, bacteria, top_N):
    df = pd.read_csv(merged_tsv_path, sep="\t")
    df.columns = df.columns.str.replace('/', '_').str.replace(' ', '_')
    df = df.apply(lambda col: col.map(lambda x: x.strip() if isinstance(x, str) else x))
    df = df[df['Scientific_name'] != 'Homo sapiens']

    if virus:
        df = df[df['Scientific_name'].str.contains('Virus', case=False, na=False)]
        df = df.rename(columns={'Scientific_name': 'Virus_Type'})
    elif bacteria:
        df = df[~df['Scientific_name'].str.contains('Virus', case=False, na=False)]
        df = df.rename(columns={'Scientific_name': 'Bacteria_Type'})

    if top_N:
        target_column = 'Virus_Type' if virus else 'Bacteria_Type'
        top_N_categories = df[target_column].value_counts().head(top_N).index
        df = df[df[target_column].isin(top_N_categories)]

    target_column = 'Virus_Type' if virus else 'Bacteria_Type'
    categorical_cols = df.select_dtypes(include=['object']).columns.tolist()
    categorical_cols.remove(target_column)

    for col in categorical_cols:
        grouped_sum = df.groupby([target_column, col])['Nr_frag_direct_at_taxon'].mean().reset_index()

        colordict = defaultdict(int)
        random_colors = ["#{:06x}".format(random.randint(0, 0xFFFFFF)) for _ in range(len(grouped_sum[col].unique()))]
        for target, color in zip(grouped_sum[target_column].unique(), random_colors):
            colordict[target] = color

        plot_width = 1100 + 5 * len(grouped_sum[col].unique())
        plot_height = 800 + 5 * len(grouped_sum[col].unique())
        font_size = max(10, 14 - len(grouped_sum[col].unique()) // 10)

        title_prefix = "Viral" if virus else "Bacterial"
        fig = px.bar(
            grouped_sum,
            x=col,
            y='Nr_frag_direct_at_taxon',
            color=target_column,
            color_discrete_map=colordict,
            title=f"{title_prefix} Abundance by {col}"
        )

        fig.update_layout(
            xaxis=dict(tickfont=dict(size=font_size), tickangle=45),
            yaxis=dict(tickfont=dict(size=font_size)),
            title=dict(text=f'Average {title_prefix} Abundance by {col}', x=0.5, font=dict(size=16)),
            bargap=0.5,
            legend=dict(
                font=dict(size=font_size),
                x=1,
                y=1,
                traceorder='normal',
                orientation='v',
                itemwidth=30,
                itemsizing='constant',
                itemclick='toggleothers',
                itemdoubleclick='toggle'
            ),
            width=plot_width,
            height=plot_height
        )

        fig.write_image(f"{title_prefix}Abundance_by_{col}.png", format='png', scale=3)
