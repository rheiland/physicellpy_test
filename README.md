# physicellpy_test

The Python wheels for `physicellpy` are now in the latest Release as Assets. Download the appropriate one for your operating system (and architecture) and version of Python. Then run `pip install <full-name>.whl` . When new wheels are available, download and reinstall, e.g., `pip install --force-reinstall physicellpy-0.1.0-cp312-cp312-macosx_14_0_arm64.whl` 

```
# inspect the package's contents:

$ python
...
>>> import physicellpy
>>> dir(physicellpy)
['BoolParameters', 'Cell', 'CellDefinition', 'CellIntegrity', ... ]
>>> 
```

```
cd samples/heterogeneity
python heterogeneity.py
```

```
# Very prelim docs
docs/_build/html/index.html
```
