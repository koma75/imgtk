imgtk
========================================================================

Image file manipulation toolkit

ADD MY CLI DETAIL DESCRIPTION HERE

Installation
------------------------------------------------------------------------

~~~shell
> pip install imgtk
~~~

Usage
------------------------------------------------------------------------


### Subcmd 1

Subcmd description

~~~shell
> imgtk subcmd1 --option1 --argopt1 arg -v
~~~

* -o, --option1
    * description
* -a, --argopt1 ARG
    * description
* -c, --config CFG
    * CFG: Path to Configuration File (default: imgtk.yml)
* -v, --verbose
    * verbosity

### Configuration file

YAML based configuration file (default file name: imgtk.yaml)
is used to store default settings for the tool.
The command line options will take precedence over the configuration parameters.

following shows the default settings of the configuration

~~~yaml
option1: option1param
option2: option2param
optionArray:
  - item1
  - item2
optionDict:
  key1: item1
  key2: item2
  key3: item3
~~~

Known Issues
------------------------------------------------------------------------

Need to be implemented.

Development
------------------------------------------------------------------------

### Building an Executable

Install pyinstaller and package the project.
May want to use venv when executing the pyinstaller.

First, enter venv and install the local package and pyinstaller

~~~shell
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

~~~shell
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

Version History
------------------------------------------------------------------------

Date        | Version   | Changes
:--         | --:       | :--
2023.01.26  | 0.1.0     | First Release
