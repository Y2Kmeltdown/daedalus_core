import argparse
import dataclasses
import datetime
import pathlib
import json
import time
import sys

import neuromorphic_drivers as nd

dirname = pathlib.Path(__file__).resolve().parent

configuration = nd.prophesee_evk4.Configuration(
    biases=nd.prophesee_evk4.Biases(
        diff_off=102,  # default: 102
        diff_on=73,    # default: 73
    )
)

parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("serial", help="Camera serial number (for example 00050423)")
parser.add_argument(
    "--data",
    default=str(dirname / "recordings"),
    help="Path of the directory where recordings are stored",
)
parser.add_argument(
    "--backup",
    default=str("/mnt/data"),
    help="Path of the directory where recordings are backed up",
)
parser.add_argument(
    "--measurement-interval",
    default=0.1,
    type=float,
    help="Interval between temperature and illuminance measurements in seconds",
)
parser.add_argument(
    "--flush-interval",
    default=0.5,
    type=float,
    help="Maximum interval between file flushes in seconds",
)
args = parser.parse_args()

def ensure_directory(path):
    """Ensure that the directory exists."""
    try:
        pathlib.Path(path).mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"Error creating directory {path}: {e}", file=sys.stderr)

def save_to_paths(primary_path, backup_path, data, mode='wb'):
    """Attempt to save data to both primary and backup paths."""
    success_primary = False
    success_backup = False

    # Try saving to the primary path
    try:
        with open(primary_path, mode) as f:
            f.write(data)
        success_primary = True
    except Exception as e:
        print(f"Error saving to primary path {primary_path}: {e}", file=sys.stderr)

    # Try saving to the backup path
    try:
        with open(backup_path, mode) as f:
            f.write(data)
        success_backup = True
    except Exception as e:
        print(f"Error saving to backup path {backup_path}: {e}", file=sys.stderr)

    # If both fail, raise an error
    if not success_primary and not success_backup:
        print("Failed to save data to both primary and backup paths.", file=sys.stderr)

def record_5Mins():
    output_directory = pathlib.Path(args.data).resolve() / f"evk4_{args.serial}"
    backup_directory = pathlib.Path(args.backup).resolve() / f"evk4_{args.serial}"

    ensure_directory(output_directory)
    ensure_directory(backup_directory)

    start_recording = time.monotonic_ns()
    end_recording = start_recording + 300_000_000_000
    flush_interval = int(round(args.flush_interval * 1e9))
    measurement_interval = int(round(args.measurement_interval * 1e9))
    name = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")

    with nd.open(raw=True, serial=args.serial) as device:
        print(f"Successfully started EVK4 {args.serial}")
        print(f"Started Recording to {output_directory / (name + '_events.raw')}")

        # Save the camera biases (metadata)
        metadata = {
            "system_time": time.time(),
            "properties": dataclasses.asdict(device.properties()),
            "configuration": "NONE",
        }
        metadata_json = json.dumps(metadata, indent=4)

        metadata_primary_path = output_directory / f"{name}_metadata.json"
        metadata_backup_path = backup_directory / f"{name}_metadata.json"

        save_to_paths(metadata_primary_path, metadata_backup_path, metadata_json, mode='w')

        events_primary_path = output_directory / f"{name}_events.raw"
        events_backup_path = backup_directory / f"{name}_events.raw"

        samples_primary_path = output_directory / f"{name}_samples.jsonl"
        samples_backup_path = backup_directory / f"{name}_samples.jsonl"

        measurements_primary_path = output_directory / f"{name}_measurements.jsonl"
        measurements_backup_path = backup_directory / f"{name}_measurements.jsonl"

        events_primary = open(events_primary_path, "ab")
        samples_primary = open(samples_primary_path, "ab")
        measurements_primary = open(measurements_primary_path, "ab")

        # Attempt to open backup files
        try:
            events_backup = open(events_backup_path, "ab")
            samples_backup = open(samples_backup_path, "ab")
            measurements_backup = open(measurements_backup_path, "ab")
            backup_files_open = True
        except Exception as e:
            print(f"Warning: Backup files could not be opened: {e}", file=sys.stderr)
            backup_files_open = False

        events_cursor = 0
        start_time = time.monotonic_ns()
        next_flush = start_time + flush_interval
        next_measurement = start_time

        try:
            for status, packet in device:

                events_primary.write(packet)
                if backup_files_open:
                    try:
                        events_backup.write(packet)
                    except Exception as e:
                        print(f"Warning: Failed to write to backup events file: {e}", file=sys.stderr)
                        backup_files_open = False  # Stop trying to write to backup

                events_cursor += len(packet)

                # Prepare sample data
                try:
                    status_dict = dataclasses.asdict(status)
                    status_dict["events_cursor"] = events_cursor
                    sample_line = json.dumps(status_dict).encode() + b'\n'

                    samples_primary.write(sample_line)
                    if backup_files_open:
                        try:
                            samples_backup.write(sample_line)
                        except Exception as e:
                            print(f"Warning: Failed to write to backup samples file: {e}", file=sys.stderr)
                            backup_files_open = False
                except Exception as e:
                    print(f"Error processing sample data: {e}", file=sys.stderr)

                # Measurements at intervals
                if time.monotonic_ns() >= next_measurement:
                    try:
                        measurement_dict = {
                            "system_time": time.time(),
                            "temperature": device.temperature_celsius(),
                            "illuminance": device.illuminance(),
                        }
                        measurement_line = json.dumps(measurement_dict).encode() + b'\n'

                        measurements_primary.write(measurement_line)
                        if backup_files_open:
                            try:
                                measurements_backup.write(measurement_line)
                            except Exception as e:
                                print(f"Warning: Failed to write to backup measurements file: {e}", file=sys.stderr)
                                backup_files_open = False
                    except Exception as e:
                        print(f"Error obtaining measurements: {e}", file=sys.stderr)

                    next_measurement = time.monotonic_ns() + measurement_interval

                # Flush data at intervals
                if time.monotonic_ns() >= next_flush:
                    events_primary.flush()
                    samples_primary.flush()
                    measurements_primary.flush()

                    if backup_files_open:
                        try:
                            events_backup.flush()
                            samples_backup.flush()
                            measurements_backup.flush()
                        except Exception as e:
                            print(f"Warning: Failed to flush backup files: {e}", file=sys.stderr)
                            backup_files_open = False

                    next_flush = time.monotonic_ns() + flush_interval

                # Check if recording time is over
                if time.monotonic_ns() >= end_recording:
                    print(f"Finished Recording {events_primary_path}")
                    break

        finally:
            events_primary.close()
            samples_primary.close()
            measurements_primary.close()

            if backup_files_open:
                events_backup.close()
                samples_backup.close()
                measurements_backup.close()

            print("All files have been closed.")

if __name__ == "__main__":
    while True:
        record_5Mins()
