import pandas as pd
import zstandard as zstd
import os
import time
import glob
import click

# ==============================================================================
# >> COMPRESSION FUNCTIONS
# ==============================================================================
def compress_csv_directly(input_path: str, output_path: str):
    """
    Compresses a CSV file using Zstandard without any data optimization.

    Args:
        input_path (str): The path to the input CSV file.
        output_path (str): The path to save the compressed output file.
    """
    print(f"-> Compressing {os.path.basename(input_path)} directly...")
    try:
        with open(input_path, 'rb') as f_in, open(output_path, 'wb') as f_out:
            cctx = zstd.ZstdCompressor(level=15)
            f_out.write(cctx.compress(f_in.read()))
    except Exception as e:
        print(f"   Error during direct compression: {e}")


def compress_csv_with_optimization(input_path: str, output_path: str):
    """
    Optimizes CSV data types and then compresses the result using Zstandard.

    Args:
        input_path (str): The path to the input CSV file.
        output_path (str): The path to save the compressed output file.
    """
    print(f"-> Optimizing and compressing {os.path.basename(input_path)}...")
    try:
        df = pd.read_csv(input_path, low_memory=False)

        # Optimize data types
        df['lat'] = pd.to_numeric(df['lat'], downcast='float')
        df['long'] = pd.to_numeric(df['long'], downcast='float')
        df['utcDate'] = pd.to_datetime(df['utcDate'], errors='coerce')
        int_cols = ['magvar', 'roadType', 'reportRating', 'confidence', 'reliability', 'size', 'duration']
        for col in int_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce').astype('Int32')
        df['nThumbsUp'] = pd.to_numeric(df['nThumbsUp'], errors='coerce').fillna(0).astype('Int32')
        cat_cols = ['type', 'subtype', 'street', 'city']
        for col in cat_cols:
            df[col] = df[col].astype('category')
        df['reportByMunicipalityUser'] = df['reportByMunicipalityUser'].astype('boolean')
        df['uuid'] = df['uuid'].astype(str)
        df['reportDescription'].fillna('', inplace=True)

        csv_in_memory = df.to_csv(index=False).encode('utf-8')
        cctx = zstd.ZstdCompressor(level=15)
        compressed_data = cctx.compress(csv_in_memory)

        with open(output_path, 'wb') as f_out:
            f_out.write(compressed_data)

    except Exception as e:
        print(f"   Error during optimized compression: {e}")


# --- NEW BATCH PROCESSING FUNCTION ---
def batch_compress_folder(source_folder: str, compression_function):
    """
    Finds all CSV files in a folder and compresses them using the provided function.

    Args:
        source_folder (str): The folder containing CSV files.
        compression_function (function): The function to use for compression
                                         (e.g., compress_csv_directly).
    """
    # 1. Create the output directory
    output_folder = os.path.join(source_folder, "compressed_output")
    os.makedirs(output_folder, exist_ok=True)
    print(f"\n--- Starting Batch Compression ---")
    print(f"Source folder: {source_folder}")
    print(f"Output folder: {output_folder}")
    print(f"Using method: {compression_function.__name__}")
    print("-" * 35)

    # 2. Find all CSV files in the source folder
    csv_files = glob.glob(os.path.join(source_folder, "*.csv"))

    if not csv_files:
        print("No CSV files found in the source folder.")
        return

    # 3. Loop through each file and apply the compression function
    for input_file_path in csv_files:
        filename = os.path.basename(input_file_path)

        # Determine the output filename
        if compression_function == compress_csv_with_optimization:
            output_filename = f"{filename}.optimized.zst"
        else:
            output_filename = f"{filename}.zst"

        output_file_path = os.path.join(output_folder, output_filename)

        # 4. Call the provided compression function
        compression_function(input_file_path, output_file_path)

    print("-" * 35)
    print(f"Batch compression complete. {len(csv_files)} files processed.")

# ==============================================================================
# >> DECOMPRESSION FUNCTIONS
# ==============================================================================
def decompress_zst_file(input_path: str, output_path: str):
    """Decompresses a single .zst file."""
    print(f"-> Decompressing {os.path.basename(input_path)}...")
    try:
        with open(input_path, 'rb') as f_in, open(output_path, 'wb') as f_out:
            dctx = zstd.ZstdDecompressor()
            f_out.write(dctx.decompress(f_in.read()))
    except Exception as e:
        print(f"   Error during decompression: {e}")


def batch_decompress_folder(source_folder: str):
    """Finds and decompresses all .zst files in a folder."""
    # Create the output directory one level up from the source
    parent_dir = os.path.dirname(source_folder)
    output_folder = os.path.join(parent_dir, "decompressed_output")
    os.makedirs(output_folder, exist_ok=True)

    print(f"\n--- Starting Batch Decompression ---")
    print(f"Source: {source_folder}\nOutput: {output_folder}")
    print("-" * 35)

    zst_files = glob.glob(os.path.join(source_folder, "*.zst"))
    if not zst_files:
        print("No .zst files found in the source folder.")
        return

    for input_file_path in zst_files:
        filename = os.path.basename(input_file_path)

        # Determine original filename by stripping compression suffixes
        if filename.endswith(".optimized.zst"):
            output_filename = filename[:-len(".optimized.zst")]
        elif filename.endswith(".zst"):
            output_filename = filename[:-len(".zst")]
        else:
            continue  # Should not happen with glob

        output_file_path = os.path.join(output_folder, output_filename)
        decompress_zst_file(input_file_path, output_file_path)

    print("-" * 35)
    print(f"Batch decompression complete. {len(zst_files)} files processed.")


