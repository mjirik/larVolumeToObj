#! /usr/bin/python
# -*- coding: utf-8 -*-

# import funkcí z jiného adresáře
import sys
import os.path

path_to_script = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(path_to_script, "../py/computation/"))
import unittest

import step_remove_boxes_iner_faces as rmbox
import numpy as np


class HistologyTest(unittest.TestCase):
    interactiveTests = False

    #  @unittest.skipIf(not interactiveTests, "skipping while developing lar functions")
    def test_remove_double_faces(self):
        faces = [
            [1, 3, 6],
            [3, 2, 1],
            [2, 1, 4],
            [1, 3, 2],
            [1, 3, 6]]

# sort all
        for face in faces:
            face = face.sort()

        print faces
        faces_new = rmbox.removeDoubleFaces(faces)
        print faces_new
        expected_faces = np.array([
            [1, 2, 4]])

        self.assertItemsEqual(faces_new, expected_faces)



if __name__ == "__main__":
    unittest.main()
