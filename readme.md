# arrview: an N dimensional array viewer
View 2D slices of numpy arrays with arbitrarily many dimensions and edit regions of interest.

# ![arrview](docs/images/screenshot.png)

## Install
```bash
$ pip install git+https://github.com/jthacker/arrview.git
```

## Usage
```python
import numpy as np
import arrview
arr = np.random.random((256, 64, 128, 5))
arrview.view(arr)
```

## Features
* N dimensional arrays
* Viewing arrays along any of the axes
* Region of interest (ROI) editing
* ROI saving / loading
* ROI statistics, including CSV export
* Several color maps
* Contrast adjustment with middle mouse button
* Intuitive panning and zooming
