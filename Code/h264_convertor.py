import argparse
import subprocess
import os

def combine_and_convert_h264_to_mp4(input_files, output_file):
    # Create a text file listing all input files
    output_file_name = os.path.splitext(output_file)[0]
    list_file = output_file_name + '.txt'
    with open(list_file, 'w') as f:
        for file in input_files:
            f.write(f"file '{file}'\n")
    
    # Run ffmpeg command to combine and convert
    command = [
        'ffmpeg',
        '-f', 'concat',
        '-safe', '0',
        '-i', list_file,
        '-c', 'copy',
        output_file
    ]
    try:
        subprocess.run(command, check=True)
        print(f"Successfully combined and converted files to {output_file}")
    except subprocess.CalledProcessError as e:
        print(f"An error occurred: {e}")

def get_files_from_folder(folder):
    # Return a sorted list of .h264 files in the specified folder
    return sorted(
        [os.path.join(folder, f) for f in os.listdir(folder) if f.endswith('.h264')]
    )

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Combine and convert H.264 files to MP4.")
    
    # Define arguments
    parser.add_argument(
        '--folder',
        type=str,
        help="The folder containing .h264 files to convert. If specified, files will be read from this folder."
    )
    parser.add_argument(
        '--files',
        nargs='+',
        metavar='file',
        help="A list of H.264 files to convert. Provide one or more .h264 files."
    )
    parser.add_argument(
        '--output',
        type=str,
        default="output.mp4",
        help="The name of the output MP4 file."
    )
    
    args = parser.parse_args()
    
    input_files = []
    
    if args.folder:
        input_files = get_files_from_folder(args.folder)
    elif args.files:
        input_files = args.files
    else:
        print("Error: You must specify either a folder or a list of files.")
        parser.print_help()
        exit(1)
    
    if len(input_files) < 1:
        print("Error: At least one .h264 file must be provided.")
        exit(1)
    
    combine_and_convert_h264_to_mp4(input_files, args.output)
