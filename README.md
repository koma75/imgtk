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
  -c, --config <cfg>          Configuration File (default: imgtk-join.yml)
  -o, --out <out>             output filename for the generated PDF
  -t, --toc <toc>             toc file to populate PDF outline
  -e, --ext <ext>             file extensions to pick up when parsing
                              directories
  -d, --dpi <dpi>             pixel density of input image in dpi
  -P, --page-layout <layout>  page layout (/PageLayout) in the PDF document
                              catalog: SinglePage, OneColumn, TwoColumnLeft,
                              TwoColumnRight, TwoPageLeft, TwoPageRight, none
                              (default: TwoPageLeft)
  -D, --direction <dir>       reading order (/Direction) in the PDF viewer
                              preferences: L2R, R2L, none (default: R2L)
  -v, --verbose               output in verbose mode
  -h, --help                  Show this message and exit.
~~~

### Options (join)

* `-c, --config <cfg>`
  * Configuration File (default: imgtk-join.yml)
  * the name is resolved relative to the current working directory.  If the
      file does not exist, join writes the defaults shown below into it and
      then reads them back.
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
* `-P, --page-layout <layout>`
  * page layout (`/PageLayout`) written into the PDF document catalog.
      `<layout>` is one of `SinglePage`, `OneColumn`, `TwoColumnLeft`,
      `TwoColumnRight`, `TwoPageLeft`, `TwoPageRight` or `none`.
  * default: `TwoPageLeft` (a two-page spread, matching the `R2L` reading order).
  * `none` removes the `/PageLayout` entry from the PDF, including the
      `OneColumn` the PDF generator would otherwise write.  Leaving the option
      out entirely is different: it selects the default.  See "PDF viewer
      defaults (document catalog)".
* `-D, --direction <dir>`
  * predominant reading order (`/Direction`) written into the
      `ViewerPreferences` dictionary of the PDF document catalog.
      `<dir>` is one of `L2R`, `R2L` or `none`.
  * default: `R2L` (right to left), which makes viewers such as Acrobat
      open the document as a right-to-left book.
  * `none` removes `/Direction` from the PDF, letting the PDF default
      (`L2R`) apply.  Leaving the option out selects the default instead.
* `-v, --verbose`
  * output in verbose mode
  * specify twice to get debug messages
* `-h, --help`
  * Show help message

### Configuration file

YAML based configuration file (default file name: imgtk-join.yml)
is used to store default settings for the tool.
The name is resolved relative to the current working directory, and the file is
created with the defaults shown below when it is missing.
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
page_layout: TwoPageLeft
direction: R2L
~~~

### PDF viewer defaults (document catalog)

`join` writes two entries into the PDF document catalog so viewers such as
Adobe Acrobat open the generated book the way the scanned pages are meant to be
read.  Both keys follow the PDF 32000-2008 specification and can be set in the
configuration file or on the command line (command line wins):

| config key      | command line          | PDF catalog entry              | default       |
| :--             | :--                 | :--                            | :--           |
| `page_layout`   | `-P, --page-layout` | `/PageLayout` (Table 3.2)      | `TwoPageLeft` |
| `direction`     | `-D, --direction`   | `/ViewerPreferences /Direction` (Table 3.22) | `R2L` |

Valid `page_layout` values are `SinglePage`, `OneColumn`, `TwoColumnLeft`,
`TwoColumnRight`, `TwoPageLeft` and `TwoPageRight`; the two `TwoPage*` values
raise the generated file to PDF 1.5 as the specification requires.
Valid `direction` values are `L2R` and `R2L`.

Each key has three states, and they are not all the same thing:

* **omitted** from the configuration file and not given on the command line:
    the tool default shown in the table above is written to the PDF.
* **set to a value**: that value is written to the PDF.  Command-line values
    win over the configuration file.
* **`none`** (configuration file or command line): the entry is *removed* from
    the PDF, which is not the same as leaving it out of the configuration file.
    `/PageLayout` in particular is removed, overriding the `OneColumn` that the
    PDF generator would otherwise write.

Configuration values are matched case-insensitively and the separators `-`,
`_` and spaces are ignored, so `page_layout: two page left`,
`page_layout: two_page_left` and `page_layout: TwoPageLeft` all mean the same.
A bad configuration value is reported and makes `join` exit unsuccessfully; an
invalid command-line value is rejected by the option parser before any file is
written.

The PDF is written by pikepdf into a temporary file next to the target and then
renamed into place, so a failing run never leaves a half-written PDF behind, and
the temporary files are always cleaned up.  Because pikepdf (qpdf) re-serializes
the document, the generated file is not byte-identical to what the PDF
generator alone would produce.

These catalog entries are applied with pikepdf, so pikepdf is a runtime
dependency of `join`.

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
                   string give in <fmt> (default: %Y-%m-%d).  Ignored when
                   --hierarch is specified.
  -v, --verbose    output in verbose mode
  -h, --help       Show this message and exit.
~~~

### Options (sort)

* `--copy/--move`
  * specify whether the file should be copied or moved.
      Files will be copied if not specified.
* `-r, --recurse`
  * search images in SRCDIR and any subdirectories.
* `-o, --overwrite`
  * overwrite any image files in TGTDIR
* `-H, --hierarch`
  * create a folder for year, month and date in a hierarchical manner
      instead of one folder for each date.
* `-d, --dry-run`
  * dry run the command.  nothing will be moved
* `-f, --fmt DATEFORMAT`
  * format the folder name using date format string specified by DATEFORMAT
  * ignored when "-H/--hierarch" is specified.  --hierarch always nests the
      target as %Y/%m/%d regardless of the format string.
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
  -s, --hash-size <size>      hash size to use for image hashing (default: 8;
                              accepted but not implemented)
  -f, --hash-func <hashfunc>  hash function to use for comparing images
  -v, --verbose               output in verbose mode
  -h, --help                  Show this message and exit.
~~~

### Options (dedup)

* `PATH`
  * PATH with the images to check for (will not be recursed)
* `-s, --hash-size SIZE`
  * specify the hash size to use. (Default: 8)
  * NOT IMPLEMENTED: the value is only range-checked and is never passed to the
      hash functions, so every hash function runs at its own built-in default
      size and the option does not change which images are grouped.
      See Known Issues.
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

* `dedup --hash-size/-s` is accepted but not implemented.  The value is only
  range-checked ("Hash size must be a positive integer"); it is never forwarded
  to the hashing helpers, so every hash function runs at imagehash's built-in
  default size (8) and `-s 4` selects exactly the same duplicate groups as
  `-s 8`.  Marked with a `TODO:` in `imgtk/deduplicate/deduplicate.py`.
* `dedup` decides which files are images by name only.  As well as the
  documented extensions, any file whose name merely contains `.jpg` (for
  example `scan.jpg.bak`) is hashed and reports an unreadable-image error, and
  `.svg` is listed but Pillow cannot decode it without the SVG plugin.
  Unreadable files are reported and skipped; the run still succeeds.
* `sort`'s image filter lists `heic` without a leading dot, so any file whose
  name ends in `heic` (`notes-heic`, `archive-scheme`-style names) is treated as
  an image and moved/copied using its file date.  Genuine `.heic` files also
  need Pillow's HEIF/HEIC plugin to be readable.
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
and the format of the configuration file "imgtk-join.yml").

## Version History

| Date        | Version   | Changes                                         |
| :--         | --:       | :--                                             |
| 2026.04.28  | 1.2.2     | update dependencies                             |
| 2026.01.13  | 1.2.1     | Fix call to FPDF failing                        |
| 2025.09.12  | 1.2.0     | Parallelize dedup feature (x6 speedup on 8core) |
| 2025.07.10  | 1.1.1     | fix Version History                             |
| 2025.07.10  | 1.1.0     | Bump Pillow to 11.x                             |
| 2023.11.28  | 1.0.1     | fix issues with Readme.                         |
| 2023.11.12  | 1.0.0     | Bump to 1.0.0.  Update Pillow to latest         |
| 2023.01.26  | 0.1.0     | First Release                                   |
