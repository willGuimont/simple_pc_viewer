# simple_pc_viewer

[Video of the viewer in action](https://www.youtube.com/shorts/H557pRHr0Bg).

<img src="doc/screenshot.png" width="400" height="400" />

## Installation & Run

```shell
# Install dependencies
pip install -r requirements.txt
# Run with
python viewer.py data/pc.npy --labels data/labels.npy --color_map data/color_map.yaml --decimate 10
python viewer.py data/waymo_pc.npy --box_labels data/waymo_labels.npy --decimate 10 --rotate
```
