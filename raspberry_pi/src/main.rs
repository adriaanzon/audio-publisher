use nix::unistd::Uid;
use std::path::Path;
use std::process::exit;
use nix::mount::{mount, unmount, MntFlags};

fn main() {
    if !Uid::effective().is_root() {
        eprintln!("In order to mount the USB drive, root priviliges are required.");
        eprintln!("Try running the command using sudo.");
        exit(1);
    }

    watch();
}

fn watch() {
    let mut monitor = udev::MonitorBuilder::new().unwrap()
        .match_subsystem("block").unwrap()
        .listen().unwrap();

    loop {
        match monitor.iter().next() {
            None => {}
            Some(event) => {
                let action = match event.action() {
                    Ok(a) => a,
                    Err(e) => {
                        eprintln!("Error getting action: {}", e);
                        continue;
                    }
                };

                let devtype = match event.devtype() {
                    Ok(dt) => dt,
                    Err(e) => {
                        eprintln!("Error getting devtype: {}", e);
                        continue;
                    }
                };

                if action != "add" || devtype != "partition" {
                    continue;
                }

                let mount_point = format!("/mnt/{}", event.sysname());

                // Make directory
                match std::fs::create_dir_all(&mount_point) {
                    Ok(_) => {}
                    Err(e) => {
                        eprintln!("Error creating directory: {}", e);
                        continue;
                    }
                }

                // Mount
                match mount(event.devpath(), mount_point.as_str(), MntFlags::empty(), None) {
                    Ok(_) => {}
                    Err(e) => {
                        eprintln!("Error mounting: {}", e);
                        continue;
                    }
                }

                // No use of `continue` from here, must always unmount

                println!("Mounted {} at {}", event.devpath(), mount_point);

                // Upload latest recording to the cloud
                // TODO: move this block into Closure to make the watch function more flexible
                match get_latest_recording(&mount_point) {
                    Ok(recording) => upload_file(&recording),
                    Err(e) => eprintln!("Error getting latest recording: {}", e)
                }

                // Unmount
                let _ = unmount(mount_point.as_str(), MntFlags::empty());
            }
        }
    }
}

fn upload_file(file_path: &Path) {
    todo!()
}

fn get_latest_recording(mount_point: &String) -> Result<Path, &str> {
    todo!()
}
