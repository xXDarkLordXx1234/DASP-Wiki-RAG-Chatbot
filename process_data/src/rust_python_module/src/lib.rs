use pyo3::prelude::*;
use pyo3::wrap_pyfunction;
use std::fs::File;
use std::io::{Read, BufReader};
use sha2::{Sha256, Digest};
use regex::Regex;
use std::fs;
use std::path::{Path, PathBuf};
use rayon::prelude::*;


#[pyfunction]
fn map_authors(
    paths: Vec<&str>,
    author_pattern: String, 
    example_author: &str
) -> Vec<String> {
    paths.into_iter().map(|file_path| {
        let original_path = match fs::canonicalize(file_path) {
            Ok(path) => path,
            Err(_) => return example_author.to_string(),
        };

        // Construct the new path
        let directory = original_path
            .parent()
            .map(|parent| parent.join(format!("{},pfv", original_path.file_stem().unwrap_or_default().to_string_lossy())))
            .unwrap_or_else(|| PathBuf::new());

        if !directory.exists() || !directory.is_dir() {
            return example_author.to_string();
        }

        // Find the maximum version
        let version = directory.read_dir()
            .ok()
            .and_then(|entries| {
                entries.filter_map(|entry| {
                    let file_name = entry.ok()?.file_name().into_string().ok()?;
                    file_name.parse::<i32>().ok()
                }).max()
            })
            .unwrap_or(0);

        let re = Regex::new(&author_pattern).unwrap(); // Replace with your regex pattern

        let mut current_version = version;
        while current_version > 1 {
            let file_path = directory.join(current_version.to_string());
            if let Ok(mut file) = fs::File::open(&file_path) {
                let mut first_bytes = vec![0; 1024]; // Read first 1024 bytes
                if file.read(&mut first_bytes).is_ok() {
                    let content = String::from_utf8_lossy(&first_bytes); // Corrected usage
                    if let Some(captures) = re.captures(&content) {
                        if let Some(author) = captures.get(1) {
                            if author.as_str() != example_author {
                                return author.as_str().to_string();
                            }
                        }
                    }
                }
            }
            current_version -= 1;
        }

        example_author.to_string()
    }).collect()
}

/// Scans a directory recursively and returns a vector of file paths that meet specific conditions.
///
/// # Arguments
///
/// * `dir` - The path to the directory to scan.
/// * `ignored_files` - A list of filenames to ignore.
/// * `min_file_size` - The minimum file size in bytes for a file to be included.
///
/// # Returns
///
/// * A vector of file paths as strings.
pub fn get_files(
    directory: String,
    ignored_files: Option<Vec<String>>,
    min_file_size: Option<u64>,
) -> Vec<String> {
    let ignored_files = ignored_files.unwrap_or_else(Vec::new);
    let min_file_size = min_file_size.unwrap_or(0);

    let dir = Path::new(&directory);
    let mut filtered_paths = Vec::new();

    if let Ok(entries) = fs::read_dir(dir) {
        for entry in entries.flatten() {
            let path = entry.path();

            if path.is_file() {
                let file_name = path.file_name()
                    .and_then(|name| name.to_str())
                    .unwrap_or("")
                    .to_string();

                let file_stem = path.file_stem()
                    .and_then(|stem| stem.to_str())
                    .unwrap_or("")
                    .to_string();

                let file_size = path.metadata().map(|meta| meta.len()).unwrap_or(0);

                if !(file_name.chars().all(|c| c.is_numeric())
                    || (file_stem.chars().all(|c| c.is_numeric())
                        && path.extension().and_then(|ext| ext.to_str()) == Some("m")))
                    && !ignored_files.contains(&file_name)
                    && file_size > min_file_size
                {
                    filtered_paths.push(path.to_string_lossy().to_string());
                }
            } else if path.is_dir() {
                filtered_paths.extend(get_files(
                    path.to_string_lossy().to_string(),
                    Some(ignored_files.clone()),
                    Some(min_file_size),
                ));
            }
        }
    }

    filtered_paths
}


/// Computes the SHA-256 hash of files at the given paths and searches for regex patterns
/// in the first 1024 bytes of each file.
///
/// # Arguments
///
/// * `paths` - A vector of strings representing file paths.
/// * `regex_patterns` - A vector of regex patterns to search for in the first 1024 bytes.
///
/// # Returns
///
/// * A vector of tuples where each tuple contains the file path, an `Option<String>` for the hash,
///   and a `Vec<String>` with all regex matches found in the first 1024 bytes.
#[pyfunction]
fn search_paths(
    paths: Vec<String>,
    regex_patterns: Option<Vec<String>>,
) -> Vec<(String, Option<String>, Vec<String>)> {
    let regex_patterns = regex_patterns.unwrap_or_else(Vec::new);

    // Compile all regex patterns into `Regex` objects.
    let regex_objects: Vec<Regex> = regex_patterns
        .iter()
        .filter_map(|pattern| Regex::new(pattern).ok())
        .collect();

    // Use rayon's `par_iter` to process paths in parallel.
    paths
        .par_iter() // Parallel iterator
        .map(|path| {
            let mut matches = Vec::new();
            let hash_result = match File::open(path) {
                Ok(file) => {
                    let mut reader = BufReader::new(file);
                    let mut hasher = Sha256::new();
                    let mut buffer = [0; 8192];
                    let mut header = Vec::new();

                    while let Ok(bytes_read) = reader.read(&mut buffer) {
                        if bytes_read == 0 {
                            break;
                        }
                        hasher.update(&buffer[..bytes_read]);

                        if header.len() < 1024 {
                            let remaining_space = 1024 - header.len();
                            header.extend_from_slice(&buffer[..bytes_read.min(remaining_space)]);
                        }
                    }

                    let header_str = String::from_utf8_lossy(&header);

                    for regex in &regex_objects {
                        if let Some(captures) = regex.captures(&header_str) {
                            if let Some(value) = captures.get(1) {
                                matches.push(value.as_str().to_string());
                            } else {
                                matches.push(captures.get(0).unwrap().as_str().to_string());
                            }
                        } else {
                            matches.push("".to_string());
                        }
                    }

                    Some(format!("{:x}", hasher.finalize()))
                }
                Err(_) => None,
            };

            (path.clone(), hash_result, matches)
        })
        .collect()
}


#[pyfunction]
fn search_directory(
    directory: String,
    regex_patterns: Vec<String>,
    ignored_files: Option<Vec<String>>,
    min_file_size: Option<u64>,
) -> Vec<(String, Option<String>, Vec<String>)> {
    search_paths(get_files(directory, ignored_files, min_file_size), Some(regex_patterns))
}


/// The Python module definition.
#[pymodule]
fn rust_python_module(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(search_paths, m)?)?;
    m.add_function(wrap_pyfunction!(search_directory, m)?)?;
    m.add_function(wrap_pyfunction!(map_authors, m)?)?;

    Ok(())
}
