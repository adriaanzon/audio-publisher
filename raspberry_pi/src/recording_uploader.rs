use google_cloud_storage::client::{Client, ClientConfig};
use google_cloud_storage::http::objects::upload::{Media, UploadObjectRequest, UploadType};
use std::io::BufRead;
use std::io::Write;
use std::path::PathBuf;
use std::time::SystemTime;
use tokio::fs::File;
use tokio_util::io::ReaderStream;

// TODO: don't use unwrap, but return a Result so the caller has a chance to unmount the drive

/// Upload the given files to the Google Cloud bucket
pub async fn upload_files(file_paths: Vec<PathBuf>) {
    if false {
        let config = ClientConfig::default().with_auth().await.unwrap();
        let client = Client::new(config);

        // Upload the file
        for file_path in file_paths.into_iter() {
            let file_name = file_path.file_name().unwrap().to_string_lossy().to_string();
            let upload_type = UploadType::Simple(Media::new(file_name));

            let file = File::open(file_path.clone()).await.unwrap();
            let file_stream = ReaderStream::new(file);

            let _uploaded = client
                .upload_streamed_object(
                    &UploadObjectRequest {
                        bucket: "bucket".to_string(),
                        ..Default::default()
                    },
                    file_stream,
                    &upload_type,
                )
                .await;
        }
    } else {
        println!("not yet implemented: upload files to Google Cloud Storage.");
        println!("needs authentication environment variables to be set.");
        for file_path in file_paths.iter() {
            println!("uploading file: {}", file_path.display());
        }
    }
}

pub fn get_new_recordings(mount_point: &str) -> Vec<PathBuf> {
    let wav_files = std::fs::read_dir(mount_point)
        .unwrap()
        // Filter out all those directory entries which couldn't be read
        .filter_map(|res| res.ok())
        // Filter files only
        .filter(|entry| entry.metadata().unwrap().is_file())
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

    match get_latest_recording_timestamp() {
        // Filter out all paths with timestamps older than the latest recording timestamp
        Some(timestamp) => wav_files
            .iter()
            .filter_map(|entry| {
                let metadata = entry.metadata().unwrap();
                let created = metadata
                    .created()
                    .unwrap()
                    .duration_since(SystemTime::UNIX_EPOCH)
                    .unwrap()
                    .as_secs();
                if created > timestamp {
                    Some(entry.clone())
                } else {
                    None
                }
            })
            .collect(),
        // If there is no latest recording timestamp (when the program is run for the first time),
        // just return the latest recording
        None => {
            match wav_files.iter().max_by_key(|entry| {
                entry
                    .metadata()
                    .unwrap()
                    .created()
                    .unwrap()
                    .duration_since(SystemTime::UNIX_EPOCH)
                    .unwrap()
                    .as_secs()
            }) {
                Some(file) => vec![file.to_path_buf()],
                None => vec![],
            }
        }
    }
}

// Store all timestamps of the latest recordings in a file,
pub fn mark_as_uploaded(new_recordings: Vec<PathBuf>) {
    let mut timestamps = new_recordings
        .iter()
        .map(|entry| {
            entry
                .metadata()
                .unwrap()
                .created()
                .unwrap()
                .duration_since(SystemTime::UNIX_EPOCH)
                .unwrap()
                .as_secs()
        })
        .collect::<Vec<_>>();
    timestamps.sort();

    ensure_lib_dir();
    let mut file = std::fs::OpenOptions::new()
        .append(true)
        .create(true)
        .open("/var/lib/audio-publisher/uploaded_recordings.txt")
        .unwrap();

    for timestamp in timestamps {
        writeln!(file, "{}", timestamp).unwrap();
    }
}

// get the last line of the file
fn get_latest_recording_timestamp() -> Option<u64> {
    ensure_lib_dir();

    let file = std::fs::OpenOptions::new()
        .read(true)
        .open("/var/lib/audio-publisher/uploaded_recordings.txt");

    match file {
        Ok(f) => match std::io::BufReader::new(f).lines().last() {
            Some(line) => Some(line.unwrap().parse().unwrap()),
            None => None,
        },
        Err(_) => None,
    }
}

fn ensure_lib_dir() {
    std::fs::create_dir_all("/var/lib/audio-publisher").unwrap();
}
