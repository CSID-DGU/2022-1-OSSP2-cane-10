# -*- coding: utf-8 -*-
"""SegModule.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1YWoFMhcl30GWs2ii0b_6LVGv1rEBiR9D
"""
# predict on jpg files or mp4 video

import cv2
import torch
from glob import glob
import os
import os.path as osp
from pathlib import Path
from torchvision import transforms
from modules.dataloaders.utils import decode_segmap
from modules.models.deeplab_xception import DeepLabv3_plus
from modules.models.sync_batchnorm.replicate import patch_replication_callback
import numpy as np
from PIL import Image
from tqdm import tqdm

### RUN OPTIONS ###
MODEL_PATH = "../model_iou_77.pth.tar"
# MODEL_PATH = "/content/drive/MyDrive/Watch_Out/model_iou.pth.tar"
ORIGINAL_HEIGHT = 720
ORIGINAL_WIDTH = 1280
MODEL_HEIGHT = 512
MODEL_WIDTH = 1024
NUM_CLASSES = 7  # including background
CUDA = True if torch.cuda.is_available() else False

MODE = 'jpg'  # 'mp4' or 'jpg'
# .mp4 path or folder containing jpg images
DATA_PATH = '/content/drive/MyDrive/Watch_Out/processed/test'
# where video file or jpg frames folder should be saved.
OUTPUT_PATH = '/content/drive/MyDrive/Watch_Out/processed/output'

# MODE = 'mp4'
# DATA_PATH = '/content/drive/MyDrive/Watch_Out/processed/test/street3.mp4'
# OUTPUT_PATH = '/content/drive/MyDrive/Watch_Out/processed/output/test.mp4'

SHOW_OUTPUT = True if 'DISPLAY' in os.environ else False  # whether to cv2.show()

OVERLAPPING = True  # whether to mix segmentation map and original image
FPS_OVERRIDE = 60  # None to use original video fps

CUSTOM_COLOR_MAP = [
    [0, 0, 0],  # background => 0
    [255, 128, 0],  # bike_lane => 1
    [255, 0, 0],  # caution_zone => 2
    [255, 0, 255],  # crosswalk => 3
    [255, 255, 0],  # guide_block => 4
    [0, 0, 255],  # roadway => 5
    [0, 255, 0],  # sidewalk => 6
]  # To ignore unused classes while predicting

CUSTOM_N_CLASSES = len(CUSTOM_COLOR_MAP)
######


class FrameGeneratorMP4:
    def __init__(self, mp4_file: str, output_path=None, show=True):
        assert osp.isfile(
            mp4_file), "DATA_PATH should be existing mp4 file path."
        self.vidcap = cv2.VideoCapture(mp4_file)
        self.fps = int(self.vidcap.get(cv2.CAP_PROP_FPS))
        self.total = int(self.vidcap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.show = show
        self.output_path = output_path

        if self.output_path is not None:
            os.makedirs(osp.dirname(output_path), exist_ok=True)
            self.fourcc = cv2.VideoWriter_fourcc(*'DIVX')

            if FPS_OVERRIDE is not None:
                self.fps = int(FPS_OVERRIDE)
            self.out = cv2.VideoWriter(
                OUTPUT_PATH, self.fourcc, self.fps, (ORIGINAL_WIDTH, ORIGINAL_HEIGHT))

    def __iter__(self):
        success, image = self.vidcap.read()
        for i in range(0, self.total):
            if success:
                img = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                yield np.array(img)

            success, image = self.vidcap.read()

    def __len__(self):
        return self.total

    def write(self, rgb_img):
        bgr = cv2.cvtColor(rgb_img, cv2.COLOR_RGB2BGR)

        if self.show:
            cv2.imshow('output', bgr)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                print('User Interrupted')
                self.close()
                exit(1)

        if self.output_path is not None:
            self.out.write(bgr)

    def close(self):
        cv2.destroyAllWindows()
        self.vidcap.release()
        if self.output_path is not None:
            self.out.release()


class FrameGeneratorJpg:
    def __init__(self, jpg_folder: str, output_folder=None, show=True):
        assert osp.isdir(
            jpg_folder), "DATA_PATH should be directory including jpg files."
        self.files = sorted(
            glob(osp.join(jpg_folder, '*.jpg'), recursive=False))
        self.show = show
        self.output_folder = output_folder
        self.last_file_name = ""

        if self.output_folder is not None:
            os.makedirs(output_folder, exist_ok=True)

    def __iter__(self):
        for file in self.files:
            img = cv2.imread(file, cv2.IMREAD_COLOR)
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            self.last_file_name = str(Path(file).name)
            yield np.array(img)

    def __len__(self):
        return len(self.files)

    def write(self, rgb_img):
        bgr = cv2.cvtColor(rgb_img, cv2.COLOR_RGB2BGR)

        if self.show:
            cv2.imshow('output', bgr)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                print('User Interrupted')
                self.close()
                exit(1)

        if self.output_folder is not None:
            path = osp.join(self.output_folder, f'{self.last_file_name}')
            cv2.imwrite(path, bgr)

    def close(self):
        cv2.destroyAllWindows()


class ModelWrapper:
    def __init__(self):
        self.composed_transform = transforms.Compose([
            transforms.Resize((MODEL_HEIGHT, MODEL_WIDTH),
                              interpolation=Image.BILINEAR),
            transforms.ToTensor(),
            transforms.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225))])

        self.model = self.load_model(MODEL_PATH)

    @staticmethod
    def load_model(model_path):
        model = DeepLabv3_plus(nInputChannels=3, n_classes=NUM_CLASSES, os=16)
        if CUDA:
            model = torch.nn.DataParallel(model, device_ids=[0])
            patch_replication_callback(model)
            model = model.cuda()
        if not osp.isfile(MODEL_PATH):
            raise RuntimeError(
                "=> no checkpoint found at '{}'".format(model_path))
        checkpoint = torch.load(model_path, torch.device(
            'cuda') if CUDA else torch.device('cpu'))
        if CUDA:
            model.module.load_state_dict(checkpoint['state_dict'])
        else:
            model.load_state_dict(checkpoint['state_dict'])
        print("=> loaded checkpoint '{}' (epoch: {}, best_pred: {})"
              .format(model_path, checkpoint['epoch'], checkpoint['best_pred']))
        model.eval()
        return model

    def run(self, rgb_img: np.array):
        x = self.composed_transform(Image.fromarray(rgb_img))
        x = x.unsqueeze(0)

        if CUDA:
            x = x.cuda()
        with torch.no_grad():
            output = self.model(x)
        pred = output.data.detach().cpu().numpy()
        pred = np.argmax(pred, axis=1).squeeze(0)
        segmap = decode_segmap(
            pred, dataset='custom', label_colors=CUSTOM_COLOR_MAP, n_classes=CUSTOM_N_CLASSES)
        segmap = np.array(segmap * 255).astype(np.uint8)

        resized = cv2.resize(segmap, (ORIGINAL_WIDTH, ORIGINAL_HEIGHT),
                             interpolation=cv2.INTER_NEAREST)
        return resized


class SegModule:
    def __init__(self):
        self.model = ModelWrapper()

    def test_predict(self):
        if MODE == 'mp4':
            generator = FrameGeneratorMP4(
                DATA_PATH, OUTPUT_PATH, show=SHOW_OUTPUT)
        elif MODE == 'jpg':
            generator = FrameGeneratorJpg(
                DATA_PATH, OUTPUT_PATH, show=SHOW_OUTPUT)
        else:
            raise NotImplementedError('MODE should be "mp4" or "jpg".')

        for index, img in enumerate(tqdm(generator)):
            segmap = self.model.run(img)
            if OVERLAPPING:
                h, w, _ = np.array(segmap).shape
                img_resized = cv2.resize(img, (w, h))
                result = (img_resized * 0.5 + segmap * 0.5).astype(np.uint8)
            else:
                result = segmap
            generator.write(result)

        generator.close()
        print('Done.')
        return segmap, result

    def predict(self, im):
        if type(im) != np.ndarray:
            im = cv2.imread(im)
        segmap = self.model.run(im)
        if OVERLAPPING:
            h, w, _ = np.array(segmap).shape
            img_resized = cv2.resize(im, (w, h))
            result = (img_resized * 0.5 + segmap * 0.5).astype(np.uint8)
        else:
            result = segmap

        print('Done.')
        return segmap, result


def convert(arr):
    i = 0
    for c in CUSTOM_COLOR_MAP:
        arr[(arr == c).all(axis=2)] = [i]
        i += 1

    return arr[:, :, 0]


if __name__ == "__main__":
    SegModel = SegModule()

    # segmap, res = SegModel.predict("/content/drive/MyDrive/Surface_001/MP_SEL_SUR_000001.jpg")
    im = cv2.imread("/content/drive/MyDrive/Surface_001/MP_SEL_SUR_000001.jpg")
    segmap, res = SegModel.predict(im)

    # segmap, res = SegModel.test_predict()

    print(segmap.shape)  # 1280 x 720 (R, G, B)

    print(res)

    cv2.imshow('seg_map', segmap)

    cv2.imshow('seg_image', res)
