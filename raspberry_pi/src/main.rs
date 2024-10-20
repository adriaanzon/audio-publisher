use crate::recording_uploader::{get_new_recordings, mark_as_uploaded, upload_files};
use nix::unistd::Uid;
use std::process::exit;

mod recording_uploader;
mod usb_drive_watcher;

#[tokio::main]
async fn main() {
    if !Uid::effective().is_root() {
        eprintln!("In order to mount the USB drive, root priviliges are required.");
        eprintln!("Try running the command using sudo.");
        exit(1);
    }

    usb_drive_watcher::watch(|mount_point| {
        let mount_point = mount_point.to_string();

        async move {
            let new_recordings = get_new_recordings(&mount_point)?;

            upload_files(new_recordings.clone()).await?;
            mark_as_uploaded(new_recordings)?;

            Ok(())
        }
    })
    .await;
}
