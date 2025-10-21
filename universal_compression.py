import os
import glob
import time
import zstandard as zstd
import click

# ==============================================================================
# >> HELPER FUNCTION
# ==============================================================================

def format_bytes(size_bytes):
    """Converts bytes to a human-readable format (KB, MB, GB)."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024**2:
        return f"{size_bytes/1024:.2f} KB"
    elif size_bytes < 1024**3:
        return f"{size_bytes/1024**2:.2f} MB"
    else:
        return f"{size_bytes/1024**3:.2f} GB"


# ==============================================================================
# >> CORE LOGIC
# ==============================================================================

def compress_file(input_path: str, output_path: str):
    """
    Compresses a single file using Zstandard and returns its original and new size.
    """
    original_size = os.path.getsize(input_path)
    try:
        with open(input_path, 'rb') as f_in, open(output_path, 'wb') as f_out:
            cctx = zstd.ZstdCompressor(level=15) # Good balance of speed and ratio
            f_out.write(cctx.compress(f_in.read()))
        compressed_size = os.path.getsize(output_path)
        return original_size, compressed_size
    except Exception:
        return original_size, -1 # Return -1 on failure

def decompress_file(input_path: str, output_path: str):
    """
    Decompresses a single .zst file and returns its original and new size.
    """
    original_size = os.path.getsize(input_path)
    try:
        with open(input_path, 'rb') as f_in, open(output_path, 'wb') as f_out:
            dctx = zstd.ZstdDecompressor()
            f_out.write(dctx.decompress(f_in.read()))
        decompressed_size = os.path.getsize(output_path)
        return original_size, decompressed_size
    except Exception:
        return original_size, -1 # Return -1 on failure


# ==============================================================================
# >> COMMAND-LINE INTERFACE (CLI)
# ==============================================================================

@click.group()
def cli():
    """A universal CLI tool to compress and decompress folders of CSV files."""
    pass


@cli.command()
@click.argument('source_dir', type=click.Path(exists=True, file_okay=False, readable=True))
@click.argument('target_dir', type=click.Path(file_okay=False, writable=True))
def compress(source_dir, target_dir):
    """Compresses all .csv files from SOURCE_DIR into TARGET_DIR."""

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_folder = os.path.join(target_dir, f"compressed_{timestamp}")
    os.makedirs(output_folder, exist_ok=True)

    click.echo(f"Source: {os.path.abspath(source_dir)}")
    click.echo(f"Target: {os.path.abspath(output_folder)}\n")

    csv_files = glob.glob(os.path.join(source_dir, "*.csv"))
    if not csv_files:
        click.echo("No .csv files found in the source directory.")
        return

    total_original_size = 0
    total_compressed_size = 0

    for input_path in csv_files:
        filename = os.path.basename(input_path)
        output_path = os.path.join(output_folder, f"{filename}.zst")

        orig_size, comp_size = compress_file(input_path, output_path)

        if comp_size != -1:
            ratio = orig_size / comp_size if comp_size > 0 else 0
            total_original_size += orig_size
            total_compressed_size += comp_size
            click.echo(
                f"✓ Compressed {filename} ({format_bytes(orig_size)} -> {format_bytes(comp_size)}, Ratio: {ratio:.2f}:1)")
        else:
            click.echo(f"✗ Failed to compress {filename}")

    # --- Overall Summary ---
    if total_original_size > 0:
        overall_ratio = total_original_size / total_compressed_size if total_compressed_size > 0 else 0
        click.echo("\n--- Compression Summary ---")
        click.echo(f"Files processed: {len(csv_files)}")
        click.echo(f"Total original size:    {format_bytes(total_original_size)}")
        click.echo(f"Total compressed size:  {format_bytes(total_compressed_size)}")
        click.echo(f"Overall compression ratio: {overall_ratio:.2f}:1")


@cli.command()
@click.argument('source_dir', type=click.Path(exists=True, file_okay=False, readable=True))
@click.argument('target_dir', type=click.Path(file_okay=False, writable=True))
def decompress(source_dir, target_dir):
    """Decompresses all .zst files from SOURCE_DIR into TARGET_DIR."""

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_folder = os.path.join(target_dir, f"decompressed_{timestamp}")
    os.makedirs(output_folder, exist_ok=True)

    click.echo(f"Source: {os.path.abspath(source_dir)}")
    click.echo(f"Target: {os.path.abspath(output_folder)}\n")

    zst_files = glob.glob(os.path.join(source_dir, "*.zst"))
    if not zst_files:
        click.echo("No .zst files found in the source directory.")
        return

    for input_path in zst_files:
        filename = os.path.basename(input_path)
        output_filename = filename[:-len(".zst")] if filename.endswith(".zst") else filename
        output_path = os.path.join(output_folder, output_filename)

        decompress_file(input_path, output_path)
        click.echo(f"✓ Decompressed {filename} -> {output_filename}")


if __name__ == "__main__":
    cli()