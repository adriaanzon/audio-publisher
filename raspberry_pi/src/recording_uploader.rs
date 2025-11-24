use google_cloud_storage::client::Storage;
use std::error::Error;
use std::io::BufRead;
use std::io::Write;
use std::path::PathBuf;
use std::time::SystemTime;
use tokio::fs::File;

/// Upload the given files to the Google Cloud bucket
pub async fn upload_files(file_paths: Vec<PathBuf>) -> Result<(), Box<dyn Error>> {
    let bucket_name = std::env::var("GCS_BUCKET")
        .map_err(|_| "GCS_BUCKET environment variable must be set")?;

    let storage = Storage::builder().build().await?;
    let bucket = format!("projects/_/buckets/{}", bucket_name);

    println!("Uploading {} file(s) to bucket: {}", file_paths.len(), bucket_name);

    // Upload the file
    for file_path in file_paths.into_iter() {
        let file_name = file_path
            .file_name()
            .ok_or("error getting file name")?
            .to_string_lossy()
            .to_string();

        println!("Uploading: {}", file_name);

        let file = File::open(&file_path).await?;

        storage
            .write_object(&bucket, &file_name, file)
            .send_buffered()
            .await?;

        println!("Successfully uploaded: {}", file_name);
    }

    Ok(())
}

pub fn get_new_recordings(mount_point: &str) -> Result<Vec<PathBuf>, Box<dyn Error>> {
    let wav_files = std::fs::read_dir(mount_point)?
        // Filter out all those directory entries which couldn't be read
        .filter_map(|res| res.ok())
        // Filter files only
        .filter(|entry| entry.metadata().map(|m| m.is_file()).unwrap_or(false))
        // Filter R_*.wav files only
        .filter_map(|entry| {
            let path = entry.path();
            if path.extension().and_then(|ext| ext.to_str()) == Some("wav")
                && path
                    .file_name()
                    .and_then(|name| name.to_str())
                    .map_or(false, |name| name.starts_with("R_"))
            {
                Some(path)
            } else {
                None
            }
        })
        .collect::<Vec<PathBuf>>();

    Ok(match get_latest_recording_timestamp_from_state() {
        // Filter out all paths with timestamps older than the latest recording timestamp
        Some(timestamp) => wav_files
            .iter()
            .filter_map(|entry| {
                let created = get_timestamp_for_path(entry).ok()?;

                if created > timestamp {
                    Some(entry.clone())
                } else {
                    None
                }
            })
            .collect(),
        // If there is no latest recording timestamp (when the program is run for the first time),
        // just return the latest recording
        None => match get_latest_path(&wav_files) {
            Some(file) => vec![file],
            None => vec![],
        },
    })
}

// Store all timestamps of the latest recordings in a file,
pub fn mark_as_uploaded(new_recordings: Vec<PathBuf>) -> Result<(), Box<dyn Error>> {
    let mut timestamps = new_recordings
        .iter()
        .filter_map(|path| get_timestamp_for_path(path).ok())
        .collect::<Vec<_>>();
    timestamps.sort();

    ensure_lib_dir()?;
    let mut file = std::fs::OpenOptions::new()
        .append(true)
        .create(true)
        .open("/var/lib/audio-publisher/uploaded_recordings.txt")?;

    for timestamp in timestamps {
        writeln!(file, "{}", timestamp)?;
    }

    Ok(())
}

/// Get the last line of the file that stores the timestamps of the uploaded recordings
fn get_latest_recording_timestamp_from_state() -> Option<u64> {
    ensure_lib_dir().ok()?;

    let file = std::fs::OpenOptions::new()
        .read(true)
        .open("/var/lib/audio-publisher/uploaded_recordings.txt");

    match file {
        Ok(f) => match std::io::BufReader::new(f).lines().last() {
            Some(line) => line.ok()?.parse().ok(),
            None => None,
        },
        Err(_) => None,
    }
}

fn ensure_lib_dir() -> Result<(), std::io::Error> {
    std::fs::create_dir_all("/var/lib/audio-publisher")?;

    Ok(())
}

fn get_timestamp_for_path(path: &PathBuf) -> Result<u64, Box<dyn Error>> {
    let timestamp = path
        .metadata()?
        .created()?
        .duration_since(SystemTime::UNIX_EPOCH)?
        .as_secs();

    Ok(timestamp)
}

fn get_latest_path(paths: &[PathBuf]) -> Option<PathBuf> {
    paths
        .iter()
        .filter_map(|path| {
            get_timestamp_for_path(path)
                .ok()
                .map(|timestamp| (timestamp, path))
        })
        .max_by_key(|(timestamp, _)| *timestamp)
        .map(|(_, path)| path.to_path_buf())
}
