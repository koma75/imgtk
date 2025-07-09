# imgtk

Image file manipulation toolkit

This tool provides image file manipulation subcommands.  Currently
supported commands are as follows:

| sub command   | Description                                       |
| :--           | :--                                               |
| join          | Join multiple image files into one PDF file.      |
| sort          | Sort image files into folders using exif date     |
| dedup         | Find duplicate images in folder using image hash  |

## Installation

~~~console
> pip install imgtk
~~~

Note: Strongly recomend using pipx to isolate package dependencies.

## Usage : join

Convert set of images to PDF.

This tool is intended to merge multiple scanned images into one PDF file.
The tool will take multiple images in order, a directory of images or
both and merge them into a PDF file in the order it is given.
Images in the directory will be searched by specified extensions and sorted by name.

~~~console
Usage: imgtk join [OPTIONS] [IMG]...

  Join images into one PDF file

Options:
  -c, --config <cfg>  Configuration File (default: imgtk-join.yml)
  -o, --out <out>     output filename for the generated PDF
  -t, --toc <toc>     toc file to populate PDF outline
  -e, --ext <ext>     file extensions to pick up when parsing directories
  -d, --dpi <dpi>     pixel density of input image in dpi
  -v, --verbose       output in verbose mode
  -h, --help          Show this message and exit.
~~~

### Options (join)

* `-c, --config <cfg>`
  * Configuration File (default: i2p.yml)
* `-o, --out <out>`
  * output filename for the generated PDF
* `-t, --toc <toc>`
  * toc file to populate PDF outline (TBD)
* `-e, --ext <ext>`
  * file extensions to pick up when parsing directories.
      directories will be searched for all files using this extensions.
  * can set multiple items.
* `-d, --dpi <dpi>`
  * pixel density of input image in dpi.  used to calculate image width and
      height in mm.
* `-v, --verbose`
  * output in verbose mode
  * specify twice to get debug messages
* `-h, --help`
  * Show help message

### Configuration file

YAML based configuration file (default file name: imgtk-join.yaml)
is used to store default settings for the tool.
The command line options will take precedence over the configuration parameters.

Following shows the default settings of the configuration

~~~yaml
out: output.pdf
toc: toc.yml
dpi: 96
ext:
  - jpg
  - jpeg
  - png
~~~

### TOC File (default name: toc.yml)

Consist of dictionary with following structure, where `level` is the
outline level (starting from 0), and `title` is the title of the
outline and will be inserted at `pagenum`.  The keys are case
sensitive.

~~~yaml
pagenum:
    - level: Num
      title: 'Title'
~~~

Note, each entry inside the page must be an array of dictionaries.
This is to allow multiple ToC item to be inserted in one page.

Example may be as follows:

~~~yaml
1:
    - level: 0
      title: 'Getting Started'
    - level: 1
      title: 'Installation'
3:
    - level: 1
      title: 'Hello, World'
5:
    - level: 0
      title: 'Programming a Guessing Game'
~~~

## Usage : sort

Command to sort image files in one folder to another by date of image
(exif meta-data or file creation date).

Moves/Copies the images inside SRCDIR into sorted folders under TGTDIR.
Target folders will be sorted based on the date the image was created
(Referes to Exif meta-data or the file creation date if exif is not
available).

~~~console
Usage: imgtk sort [OPTIONS] SRCDIR TGTDIR

  Sort and Move/Copy images from SRCDIR to TGTDIR.

Options:
  --copy           Copy files from SRCDIR to TGTDIR (Default)
  --move           Move files from SRCDIR to TGTDIR
  -r, --recurse    Search for images in SRCDIR recursively
  -o, --overwrite  Overwrite files in TGTDIR
  -H, --hierarch   Create a hierarchical directory for Year, Month and Date in
                   TGTDIR
  -d, --dry-run    Dry run the command without moving
  -f, --fmt <fmt>  Format target directory name using date format strftime
                   string give in <fmt> (default: %Y-%m-%d).
  -v, --verbose    output in verbose mode
  -h, --help       Show this message and exit.
~~~

### Options (sort)

* `--copy/--move`
  * specify whether the file should be copied or moved.
      Files will be copied if not specified.
* `-r, --recursive`
  * search images in SOURCEDIR and any subdirectories.
* `-o, --overwrite`
  * overwrite any image files in TARGETDIR
* `-H, --hierarch`
  * create a folder for year, month and date in a hierarchical manner
      instead of one folder for each date.
* `-d, --dry-run`
  * dry run the command.  nothing will be moved
* `-f, --fmt DATEFORMAT`
  * format the folder name using date format string specified by DATEFORMAT
  * ignored when "-h" is specified.
* `-v, --verbose`
  * verbose mode

## Usage : dedup

This is a tool to find similar images in a set of images using imagehash
library.  If two or more similar images are found (same hash value), the
images are moved to a subfolder for each hash value.

~~~console
Usage: imgtk dedup [OPTIONS] PATH

  Find duplicates in PATH using <hashfunc>

  <hashfunc> can be any of the following:

      ahash   : Average hash
      phash   : Perceptual hash
      dhash   : Difference hash (default)
      haar    : Haar wavelet hash
      db4     : Daubechies wavelet hash
      color   : HSV color hash
      crop    : crop-resistant hash

Options:
  -s, --hash-size <size>      hash size to use for image hashing (default:
                              dhash)
  -f, --hash-func <hashfunc>  hash function to use for comparing images
  -v, --verbose               output in verbose mode
  -h, --help                  Show this message and exit.
~~~

### Options (dedup)

* `PATH`
  * PATH with the images to check for (will not be recursed)
* `-s, --hash-size SIZE`
  * specify the hash size to use. (Default: 8)
* `-f, --hash-func`
  * ahash
    * Use Average hash to find duplicates in PATH
  * color
    * Use HSV color hash to find duplicates in PATH
  * crop
    * Use Crop resistant hash to find similar images in PATH
  * db4
    * Use Daubechies wavelet hash to find duplicates in PATH
  * dhash
    * Use Difference hash to find duplicates in PATH
  * haar
    * Use Haar wavelet hash to find duplicates in PATH
  * phash
    * Use Perceptual hash to find duplicates in PATH
* `-v, --verbose`
  * specify verbosity.  specify twice to get debug message

If two or more images with the same hash is found, they are put into the
same folder with tha hash value as the folder name.

## Known Issues

* No known issues at time of release.
* See github issues for latest issues.

## Development

### Building an Executable

Install pyinstaller and package the project.
May want to use venv when executing the pyinstaller.

First, enter venv and install the local package and pyinstaller

~~~console
>. .venv/Scripts/activate
(.venv) >pip install .
Processing /path/to/proj/imgtk
~snip~
Installing collected packages: imgtk
    Running setup.py install for imgtk ... done
Successfully installed imgtk-0.1.0

(.venv) >pip install pyinstaller
~snip~
Successfully installed pyinstaller-3.6
~~~

Use pyinstaller to build the exe file.

~~~console
(.venv) >pyinstaller imgtk\cli.py --onefile --name imgtk
~snip~
13691 INFO: Building EXE from EXE-00.toc completed successfully.
~~~

Executable should be ready in dist/imgtk.exe

### Versioning

The project will follow the [semver2.0](http://semver.org/) versioning scheme.
With initial development phase starting at 0.1.0 and increasing
minor/patch versions until we deploy the tool to production
(and reach 1.0.0).
The interface relevant to versioning is whatever defined in this
document's "Usage" section (includes all (sub)commands, their cli arguments,
and the format of the configuration file "imgtk.yaml").

## Version History

| Date        | Version   | Changes                                         |
| :--         | --:       | :--                                             |
| 2025.07.10  | 1.0.2     | Bump Pillow to 11.x                             |
| 2023.11.28  | 1.0.1     | fix issues with Readme.                         |
| 2023.11.12  | 1.0.0     | Bump to 1.0.0.  Update Pillow to latest         |
| 2023.01.26  | 0.1.0     | First Release                                   |
