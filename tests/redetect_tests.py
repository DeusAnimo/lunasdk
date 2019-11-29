import itertools
from collections import namedtuple
from typing import Optional

import pytest

from lunavl.sdk.errors.errors import LunaVLError
from lunavl.sdk.errors.exceptions import LunaSDKException
from lunavl.sdk.faceengine.facedetector import (
    FaceDetector,
    Landmarks5,
    Landmarks68,
    FaceDetection,
    ImageForRedetection)
from lunavl.sdk.faceengine.setting_provider import DetectorType
from lunavl.sdk.image_utils.geometry import Rect
from lunavl.sdk.image_utils.image import VLImage
from tests.base import BaseTestClass
from tests.resources import SEVERAL_FACES, CLEAN_ONE_FACE


class TestDetector(BaseTestClass):
    """
    Test of redetection.
    """

    detector: FaceDetector = None

    @classmethod
    def setup_class(cls):
        super().setup_class()
        cls.detector = cls.faceEngine.createFaceDetector(DetectorType.FACE_DET_DEFAULT)

    @staticmethod
    def getErrorRedetectOne(imageVl: VLImage, detection: Optional[FaceDetection] = None, bBox: Optional[Rect] = None):
        with pytest.raises(LunaSDKException) as ex:
            if bBox is None:
                TestDetector.detector.redetectOne(image=imageVl, detection=detection)
            else:
                TestDetector.detector.redetectOne(image=imageVl, bBox=bBox)
        return ex

    @staticmethod
    def getErrorRedetect(imageVl: VLImage, bBoxes):
        with pytest.raises(LunaSDKException) as ex:
            TestDetector.detector.redetect(images=[ImageForRedetection(image=imageVl, bBoxes=bBoxes)])
        return ex

    def test_detect_landmarks(self):
        imageWithOneFace = VLImage.load(filename=CLEAN_ONE_FACE)
        detectOne = TestDetector.detector.detectOne(image=imageWithOneFace)
        Case = namedtuple("Case", ("detect5Landmarks", "detect68Landmarks"))
        cases = [
            Case(landmarks5, landmarks68) for landmarks5, landmarks68 in itertools.product((True, False), (True, False))
        ]

        for case in cases:
            with self.subTest(landmarks5=case.detect5Landmarks, landmarks68=case.detect68Landmarks):
                for func in ("redetect", "redetectOne"):
                    with self.subTest(funcName=func):
                        if func == "redetectOne":
                            response = TestDetector.detector.redetectOne(
                                image=imageWithOneFace,
                                detection=detectOne,
                                detect68Landmarks=case.detect68Landmarks,
                                detect5Landmarks=case.detect5Landmarks,
                            )
                        else:
                            response = TestDetector.detector.redetect(
                                images=[ImageForRedetection(image=imageWithOneFace,
                                                            bBoxes=[detectOne.boundingBox.rect])],
                                detect68Landmarks=case.detect68Landmarks,
                                detect5Landmarks=case.detect5Landmarks,
                            )[0][0]

                        if case.detect5Landmarks:
                            assert isinstance(response.landmarks5, Landmarks5)
                        else:
                            assert response.landmarks5 is None
                        if case.detect68Landmarks:
                            assert isinstance(response.landmarks68, Landmarks68)
                        else:
                            assert response.landmarks68 is None

    def test_redetect_one_image(self):
        imageWithOneFace = VLImage.load(filename=CLEAN_ONE_FACE)
        detection = TestDetector.detector.detectOne(image=imageWithOneFace)
        for parameter in ("bBox", "detection"):
            if parameter == "bBox":
                response = TestDetector.detector.redetectOne(image=imageWithOneFace,
                                                             bBox=detection.boundingBox.rect)
            else:
                response = TestDetector.detector.redetectOne(image=imageWithOneFace,
                                                             detection=detection)
        assert isinstance(response, FaceDetection)

    def test_batch_redetect(self):
        imageWithOneFace = VLImage.load(filename=CLEAN_ONE_FACE)
        imageWithSeveralFace = VLImage.load(filename=SEVERAL_FACES)
        detectOne = TestDetector.detector.detectOne(image=imageWithOneFace)
        detectSeveral = TestDetector.detector.detect(images=[imageWithSeveralFace])
        redetect = TestDetector.detector.redetect(images=[ImageForRedetection(image=imageWithSeveralFace,
                                                                              bBoxes=[face.boundingBox.rect
                                                                                      for face in detectSeveral[0]]),
                                                          ImageForRedetection(image=imageWithOneFace,
                                                                              bBoxes=[detectOne.boundingBox.rect])])
        assert all(isinstance(face, FaceDetection) for item in redetect for face in item)
        assert 2 == len(redetect)
        assert 5 == len(redetect[0])
        assert 1 == len(redetect[1])

    def test_redetect_face_with_wrong_area(self):
        imageWithOneFace = VLImage.load(filename=CLEAN_ONE_FACE)
        redetectOne = TestDetector.detector.redetectOne(image=imageWithOneFace, bBox=Rect(0, 0, 100, 100))
        redetect = TestDetector.detector.redetect(images=[ImageForRedetection(image=imageWithOneFace,
                                                                              bBoxes=[Rect(0, 0, 100, 100)])])
        assert redetectOne is None
        assert redetect[0][0] is None

    def test_redetect_one_face_invalid_rectangle(self):
        imageWithOneFace = VLImage.load(filename=CLEAN_ONE_FACE)
        exceptionInfo = self.getErrorRedetectOne(imageVl=imageWithOneFace, bBox=Rect(0.666, 0.666, 0.666, 0.666))
        self.assertLunaVlError(exceptionInfo, 100013, LunaVLError.InvalidInput)

    def test_redetect_face_invalid_rectangle(self):
        imageWithOneFace = VLImage.load(filename=CLEAN_ONE_FACE)
        exceptionInfo = self.getErrorRedetect(imageVl=imageWithOneFace, bBoxes=[Rect()])
        self.assertLunaVlError(exceptionInfo, 99999, LunaVLError.UnknownError)

    def test_redetect_face_without_detection_and_bbox(self):
        imageWithOneFace = VLImage.load(filename=CLEAN_ONE_FACE)
        exceptionInfo = self.getErrorRedetectOne(imageVl=imageWithOneFace)
        self.assertLunaVlError(exceptionInfo, 110019, LunaVLError.DetectFacesError)