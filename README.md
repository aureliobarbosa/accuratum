# **Accuratum**
### A python library for creating *Accuratum Sundials*

## Developer instructions

To setup this project for development on Ubuntu Linux use the commands below to
- create a virtual environment
- activate it, and
- install the packages list on pyproject.toml
- install a python kernel for usage with jupyter notebooks:
```bash
$ python -m venv env
$ source env/bin/activate
$ pip install -e .["dev"]
$ python -m ipykernel install --user --name=accuratum
```

## Authors:
- Paulo Eduardo de Brito (creator)
- Marco Aurélio Alves Barbosa
