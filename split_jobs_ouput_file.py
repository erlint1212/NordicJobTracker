import os


def split_job_file(file_path, batch_size=10, output_subdir_name="job_batches"):
    """
    Splits a large text file with job ads into smaller batch files.
    """
    if not os.path.exists(file_path):
        print(f"   ⚠️ Error: Cannot find the file '{file_path}'. Skipping splitting.")
        return

    base_dir = os.path.dirname(file_path)
    if not base_dir:
        base_dir = "."

    output_dir = os.path.join(base_dir, output_subdir_name)
    os.makedirs(output_dir, exist_ok=True)

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # The exact separator used in file_manager.py
    separator = "-" * 74

    jobs = content.split(separator)
    jobs = [job.strip() for job in jobs if job.strip()]

    # First block is usually the report header ("Generated Report..."), let's exclude it if it doesn't look like a job
    if jobs and not jobs[0].startswith("JOB TITLE:"):
        jobs.pop(0)

    total_jobs = len(jobs)
    if total_jobs == 0:
        return

    print(f"   ✂️  Splitting {total_jobs} jobs into batches...")

    batch_number = 1
    for i in range(0, total_jobs, batch_size):
        batch_jobs = jobs[i : i + batch_size]
        batch_content = f"\n\n{separator}\n\n".join(batch_jobs)

        output_filename = f"{output_subdir_name}_{batch_number}.txt"
        output_filepath = os.path.join(output_dir, output_filename)

        with open(output_filepath, "w", encoding="utf-8") as out_file:
            out_file.write(batch_content)

        batch_number += 1

    print(f"   ✅ Created {batch_number - 1} batch files in '{output_dir}'.")


# This allows you to still run it standalone if you ever want to!
if __name__ == "__main__":
    input_file = "output/gemini_context.txt"
    batch_size = 10
    output_folder = "job_batches"
    split_job_file(input_file, batch_size, output_folder)
