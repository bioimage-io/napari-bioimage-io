import os
from pathlib import Path
from qtpy.QtCore import (
    QObject,
    Qt,
)
from qtpy.QtGui import QFont, QMovie
from qtpy.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
import napari
import napari.resources
from napari.utils.notifications import show_info, show_error as notify_error
from napari._qt.qt_resources import get_stylesheet, QColoredSVGIcon
import bioimageio.core as bc
from napari_bioimageio import launcher, model_manager

import numpy as np
from skimage.measure import regionprops, label
from skimage.segmentation import watershed
from skimage.transform import rescale, resize
from xarray import DataArray


HPA_CLASSES = {
    "Nucleoplasm": 0,
    "Nuclear membrane": 1,
    "Nucleoli": 2,
    "Nucleoli fibrillar center": 3,
    "Nuclear speckles": 4,
    "Nuclear bodies": 5,
    "Endoplasmic reticulum": 6,
    "Golgi apparatus": 7,
    "Intermediate filaments": 8,
    "Actin filaments": 9,
    "Focal adhesion sites": 9,
    "Microtubules": 10,
    "Mitotic spindle": 11,
    "Centrosome": 12,
    "Centriolar satellite": 12,
    "Plasma membrane": 13,
    "Cell Junctions": 13,
    "Mitochondria": 14,
    "Aggresome": 15,
    "Cytosol": 16,
    "Vesicles": 17,
    "Peroxisomes": 17,
    "Endosomes": 17,
    "Lysosomes": 17,
    "Lipid droplets": 17,
    "Cytoplasmic bodies": 17,
    "No staining": 18,
}

CELL_LINES = [
    "A-431",
    "A549",
    "EFO-21",
    "HAP1",
    "HEK 293",
    "HUVEC TERT2",
    "HaCaT",
    "HeLa",
    "PC-3",
    "RH-30",
    "RPTEC TERT1",
    "SH-SY5Y",
    "SK-MEL-30",
    "SiHa",
    "U-2 OS",
    "U-251 MG",
    "hTCEpi",
]

nuclear_segmentation_model_filter = "10.5281/zenodo.6200999"
cell_segmentation_model_filter = "10.5281/zenodo.6200635"
classification_model_filter = "10.5281/zenodo.5910854"

# TODO find a proper way to import style from napari
custom_style = get_stylesheet("dark")


class QtBioimageIOHPA(QDialog):
    def __init__(self, viewer: "napari.viewer.Viewer"):
        super().__init__()
        self._viewer = viewer
        self.setStyleSheet(custom_style)
        self.image1_layer = ""
        self.image2_layer = ""
        self.image3_layer = ""
        self.image4_layer = ""
        self.nucseg_model_id = ""
        self.nucseg_model_version = ""
        self.nucseg_id = "None"
        self.celseg_model_id = ""
        self.celseg_model_version = ""
        self.celseg_id = "None"
        self.classi_model_id = ""
        self.classi_model_version = ""
        self.classi_id = "None"

        self.setup_ui()

    def setup_ui(self):
        self.layout = QVBoxLayout()

        imageTitleBox = QHBoxLayout()
        imageTitle_label = QLabel("Layers selected:")
        imageTitle_label.setMinimumWidth(500)
        imageTitleBox.addWidget(imageTitle_label)
        imageTitleBox.addStretch()
        imageTitleBox.setContentsMargins(10, 10, 10, 0)
        self.layout.addLayout(imageTitleBox)

        image1Box = QHBoxLayout()
        image1_label = QLabel("- Nucleus:")
        self.cb_1 = QComboBox()
        for curr_layer in self._viewer.layers:
            self.cb_1.addItem(curr_layer.name)
        self.cb_1.addItem("None")
        image1Box.addWidget(image1_label, 3)
        image1Box.addWidget(self.cb_1, 7)
        image1Box.addStretch()
        image1Box.setContentsMargins(10, 0, 10, 0)
        self.layout.addLayout(image1Box)

        image2Box = QHBoxLayout()
        image2_label = QLabel("- Microtubules:")
        self.cb_2 = QComboBox()
        for curr_layer in self._viewer.layers:
            self.cb_2.addItem(curr_layer.name)
        self.cb_2.addItem("None")
        image2Box.addWidget(image2_label, 3)
        image2Box.addWidget(self.cb_2, 7)
        image2Box.addStretch()
        image2Box.setContentsMargins(10, 0, 10, 0)
        self.layout.addLayout(image2Box)

        image3Box = QHBoxLayout()
        image3_label = QLabel("- ER:")
        self.cb_3 = QComboBox()
        for curr_layer in self._viewer.layers:
            self.cb_3.addItem(curr_layer.name)
        self.cb_3.addItem("None")
        image3Box.addWidget(image3_label, 3)
        image3Box.addWidget(self.cb_3, 7)
        image3Box.addStretch()
        image3Box.setContentsMargins(10, 0, 10, 0)
        self.layout.addLayout(image3Box)

        image4Box = QHBoxLayout()
        image4_label = QLabel("- Target protein:")
        self.cb_4 = QComboBox()
        for curr_layer in self._viewer.layers:
            self.cb_4.addItem(curr_layer.name)
        self.cb_4.addItem("None")
        image4Box.addWidget(image4_label, 3)
        image4Box.addWidget(self.cb_4, 7)
        image4Box.addStretch()
        image4Box.setContentsMargins(10, 0, 10, 0)
        self.layout.addLayout(image4Box)

        modelsTitleBox = QHBoxLayout()
        modelsTitle_label = QLabel("Models:")
        modelsTitleBox.addWidget(modelsTitle_label)
        modelsTitleBox.addStretch()
        modelsTitleBox.setContentsMargins(10, 15, 10, 0)
        self.layout.addLayout(modelsTitleBox)

        nucsegBox = QHBoxLayout()
        nucseg_label = QLabel("Nucleus segmentation:")
        self.nucseg_value = QLabel(self.nucseg_id)
        nucseg_value_btn = QPushButton("Change")
        nucseg_value_btn.clicked.connect(lambda: self.get_model_file("nucseg"))
        nucsegBox.addWidget(nucseg_label)
        nucsegBox.addSpacing(10)
        nucsegBox.addWidget(self.nucseg_value)
        nucsegBox.addSpacing(10)
        nucsegBox.addWidget(nucseg_value_btn)
        nucsegBox.addStretch()
        nucsegBox.setContentsMargins(10, 0, 10, 0)
        self.layout.addLayout(nucsegBox)

        celsegBox = QHBoxLayout()
        celseg_label = QLabel("Cell segmentation:")
        self.celseg_value = QLabel(self.celseg_id)
        celseg_value_btn = QPushButton("Change")
        celseg_value_btn.clicked.connect(lambda: self.get_model_file("celseg"))
        celsegBox.addWidget(celseg_label)
        celsegBox.addSpacing(10)
        celsegBox.addWidget(self.celseg_value)
        celsegBox.addSpacing(10)
        celsegBox.addWidget(celseg_value_btn)
        celsegBox.addStretch()
        celsegBox.setContentsMargins(10, 0, 10, 0)
        self.layout.addLayout(celsegBox)

        classiBox = QHBoxLayout()
        classi_label = QLabel("Classification:")
        self.classi_value = QLabel(self.classi_id)
        classi_value_btn = QPushButton("Change")
        classi_value_btn.clicked.connect(lambda: self.get_model_file("classi"))
        classiBox.addWidget(classi_label)
        classiBox.addSpacing(10)
        classiBox.addWidget(self.classi_value)
        classiBox.addSpacing(10)
        classiBox.addWidget(classi_value_btn)
        classiBox.addStretch()
        classiBox.setContentsMargins(10, 0, 10, 0)
        self.layout.addLayout(classiBox)

        runBox = QHBoxLayout()
        self.run_btn = QPushButton("Run")
        self.run_btn.setObjectName("install_button")
        self.run_btn.clicked.connect(self.run_model)
        runBox.addWidget(self.run_btn)
        runBox.setContentsMargins(10, 20, 10, 10)
        self.layout.addLayout(runBox)

        self.layout.addStretch()
        self.setLayout(self.layout)

    def select_bioimageio_model(self, selected_model):
        model_id = selected_model[: (selected_model.rfind("/"))]
        model_version = selected_model[(selected_model.rfind("/") + 1) :]
        if self.model_selected == "nucseg":
            self.nucseg_model_id = model_id
            self.nucseg_model_version = model_version
            self.nucseg_id = model_id + "/" + model_version
            self.nucseg_value.setText(self.nucseg_id)
        elif self.model_selected == "celseg":
            self.celseg_model_id = model_id
            self.celseg_model_version = model_version
            self.celseg_id = model_id + "/" + model_version
            self.celseg_value.setText(self.celseg_id)
        elif self.model_selected == "classi":
            self.classi_model_id = model_id
            self.classi_model_version = model_version
            self.classi_id = model_id + "/" + model_version
            self.classi_value.setText(self.classi_id)

    def get_model_file(self, model_type):
        self.model_selected = model_type
        model_filter = nuclear_segmentation_model_filter
        if model_type == "celseg":
            model_filter = cell_segmentation_model_filter
        elif model_type == "classi":
            model_filter = classification_model_filter
        launcher(parent=self, model_filter=model_filter, static_filter=True)

    def run_model(self):
        if self.cb_1.currentText() == "None":
            notify_error("Please select a valid Nucleus image layer")
            return
        if self.cb_2.currentText() == "None":
            notify_error("Please select a valid Microtubules image layer")
            return
        if self.cb_3.currentText() == "None":
            notify_error("Please select a valid ER image layer")
            return
        if self.cb_4.currentText() == "None":
            notify_error("Please select a valid target protein image layer")
            return
        if self.nucseg_model_id == "":
            notify_error("Please select a valid nucleus segmentation model")
            return
        if self.celseg_model_id == "":
            notify_error("Please select a valid cell segmentation model")
            return
        if self.classi_model_id == "":
            notify_error("Please select a valid classification model")
            return

        image_paths = {}
        image_paths["plugin_cls"] = [
            [
                self.cb_2.currentText(),
                self.cb_1.currentText(),
                self.cb_4.currentText(),
                self.cb_3.currentText(),
            ]
        ]

        cell_segmentation = None
        prediction_pkl = None

        run_nucleus_model = model_manager.load_model(
            self.nucseg_model_id, self.nucseg_model_version
        )
        run_cell_model = model_manager.load_model(
            self.celseg_model_id, self.celseg_model_version
        )
        run_classification_model = model_manager.load_model(
            self.classi_model_id, self.classi_model_version
        )

        axes = run_cell_model.inputs[0].axes
        channels = ["red", "blue", "green"]
        padding = {"x": 32, "y": 32}
        scale_factor = 0.25

        def load_image(channels, scale_factor=None):
            image = []
            for chan in channels:
                np_img_chan = []
                if chan == "red":
                    np_img_chan = self._viewer.layers[self.cb_2.currentText()].data
                elif chan == "blue":
                    np_img_chan = self._viewer.layers[self.cb_1.currentText()].data
                if chan == "yellow":
                    np_img_chan = self._viewer.layers[self.cb_3.currentText()].data
                if chan == "green":
                    np_img_chan = self._viewer.layers[self.cb_4.currentText()].data
                if scale_factor is not None:
                    np_img_chan = rescale(np_img_chan, scale_factor)
                image.append(np_img_chan[None])
            image = np.concatenate(image, axis=0)

            return image

        def _segment(pp_cell, pp_nucleus):
            image = load_image(channels, scale_factor=scale_factor)

            # run prediction with the nucleus model
            input_nucleus = DataArray(
                np.concatenate([image[1:2], image[1:2], image[1:2]], axis=0)[None],
                dims=axes,
            )
            nuclei_pred = bc.prediction.predict_with_padding(
                pp_nucleus, input_nucleus, padding=padding
            )[0].values[0]

            # segment the nuclei in order to use them as seeds for the cell segmentation
            threshold = 0.5
            min_size = 250
            fg = nuclei_pred[-1]
            nuclei = label(fg > threshold)
            ids, sizes = np.unique(nuclei, return_counts=True)
            # don't apply size filter on the border
            border = np.ones_like(nuclei).astype("bool")
            border[1:-1, 1:-1] = 0
            filter_ids = ids[sizes < min_size]
            border_ids = nuclei[border]
            filter_ids = np.setdiff1d(filter_ids, border_ids)
            nuclei[np.isin(nuclei, filter_ids)] = 0

            # run prediction with the cell segmentation model
            input_cells = DataArray(image[None], dims=axes)
            cell_pred = bc.prediction.predict_with_padding(
                pp_cell, input_cells, padding=padding
            )[0].values[0]
            # segment the cells
            threshold = 0.5
            fg, bd = cell_pred[2], cell_pred[1]
            cell_seg = watershed(bd, markers=nuclei, mask=fg > threshold)

            # bring back to the orignial scale
            cell_seg = rescale(
                cell_seg,
                1.0 / scale_factor,
                order=0,
                preserve_range=True,
                anti_aliasing=False,
            ).astype(cell_seg.dtype)
            return cell_seg

        with bc.create_prediction_pipeline(bioimageio_model=run_cell_model) as pp_cell:
            with bc.create_prediction_pipeline(
                bioimageio_model=run_nucleus_model
            ) as pp_nucleus:
                cell_segmentation = _segment(pp_cell, pp_nucleus)

        axes = run_classification_model.inputs[0].axes
        expected_shape = run_classification_model.inputs[0].shape[1:]
        channels = ["red", "green", "blue", "yellow"]

        def _classifiy(pp, segmentation):
            image = load_image(channels)
            segments = regionprops(segmentation)

            seg_ids = []
            seg_images = []
            for seg in segments:
                seg_id = seg.label
                bb = np.s_[seg.bbox[0] : seg.bbox[2], seg.bbox[1] : seg.bbox[3]]

                im = image[(slice(None),) + bb]
                mask = segmentation[bb] != seg_id
                for c in range(im.shape[0]):
                    im[c][mask] = 0
                im = resize(im, expected_shape)
                # after resize the value range is in [0, 1], but the model expects a value range of [0, 255]
                # note that we could also use 'resize(..., preserve_range=True)', but we might also get other input ranges
                # and this way we can make sure that the value range for the model is [0, 255]
                im *= 255

                # for debugging
                # v = napari.Viewer()
                # v.add_image(im)
                # mask = resize(mask, expected_shape[1:], order=0, anti_aliasing=False, preserve_range=True)
                # v.add_labels(np.logical_not(mask), name="cell_mask")
                # napari.run()

                seg_ids.append(seg_id)
                seg_images.append(im[None])

            input_ = DataArray(np.concatenate(seg_images, axis=0), dims=axes)
            preds = pp(input_)[0].values
            assert preds.shape[0] == len(seg_ids)
            predictions = {seg_id: pred for seg_id, pred in zip(seg_ids, preds)}

            return predictions

        with bc.create_prediction_pipeline(
            bioimageio_model=run_classification_model
        ) as pp:
            prediction_pkl = _classifiy(pp, cell_segmentation)

        reverse_class_dict = {v: k for k, v in HPA_CLASSES.items()}

        def visualize(segmentation, pred):
            segments = regionprops(segmentation)
            bounding_boxes = []
            classes = []
            likelihoods = []
            for seg in segments:
                scores = pred[seg.label]
                if scores is None:
                    continue
                xmin, ymin, xmax, ymax = seg.bbox
                bounding_boxes.append(np.array([[xmin, ymin], [xmax, ymax]]))
                # apply softmax to find the class probabilities and the most likely class
                scores = scores.squeeze()
                scores = np.exp(scores) / np.sum(np.exp(scores))
                # most likely class
                class_id = np.argmax(scores)
                class_name = reverse_class_dict[class_id]
                classes.append(class_name)
                likelihoods.append(scores[np.argmax(scores)])

            properties = {"likelihood": likelihoods, "class": classes}
            text_properties = {
                "text": "{class}: {likelihood:0.2f}",
                "anchor": "upper_left",
                "translation": [-5, 0],
                "size": 16,
                "color": "red",
            }

            v = self._viewer
            v.add_labels(segmentation)
            v.add_shapes(
                bounding_boxes,
                properties=properties,
                text=text_properties,
                shape_type="rectangle",
                edge_width=4,
                edge_color="coral",
                face_color="transparent",
            )
            # napari.run()

        visualize(cell_segmentation, prediction_pkl)
