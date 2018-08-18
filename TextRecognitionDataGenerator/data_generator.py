import os
import cv2
import random

from PIL import Image, ImageFilter, ImageFont

from computer_text_generator import ComputerTextGenerator
try:
    from handwritten_text_generator import HandwrittenTextGenerator
except ImportError as e:
    print('Missing modules for handwritten text generation.')

from background_generator import BackgroundGenerator
from distorsion_generator import DistorsionGenerator
from elastic_distortion_generator import ElasticDistortionGenerator
import cv2
import numpy as np
from skimage.filters import threshold_niblack, rank
from skimage.morphology import disk
from fontTools.ttLib import TTFont
from PIL import Image, ImageEnhance, ImageFilter
from skimage.filters import threshold_sauvola, threshold_otsu
from pyblur import *

import random

def decision(probability):
    return random.random() < probability

def sauvola_bin(img):
    img = np.array(img)
    bin = img > threshold_sauvola(img, window_size=15, k=0.1)
    img = bin.astype('uint8') * 255
    return img

def add_random_space_to_string(s):
    s = list(s)
    for i in range(len(s) - 1):
        if s[i] == ' ':
            while random.randrange(2):
                s[i] = s[i] + ' '
    return ''.join(s)

def nick_binarize(img_list):
    '''Binarize linecut images using two differently sized local threshold kernels

    Args:
        img_list: list of grayscale linecut images
    Returns:
        results: binarized images in the same order as the input'''

    results = []

    for img in img_list:
        # img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        height = img.shape[0]
        width = img.shape[1]

        # Resize the images to 200 pixel height
        scaling_factor = 100/img.shape[0]
        new_w = int(scaling_factor*img.shape[1])
        new_h = int(scaling_factor*img.shape[0])
        # img = cv2.resize(img, (new_w, new_h))
        img = np.array(Image.fromarray(img).resize((new_w, new_h), Image.ANTIALIAS))

        # First pass thresholding
        th1 = threshold_niblack(img, 13, 0.00)

        # Second pass thresholding
        radius = 101
        structured_elem = disk(radius)
        th2 =  rank.otsu(img, structured_elem)

        # Masking
        img = (img > th1) | (img > th2)
        img = img.astype('uint8')*255

        img = np.array(Image.fromarray(img).resize((width, height), Image.ANTIALIAS))
        results.append(img)

    return results

class FakeTextDataGenerator(object):
    @classmethod
    def generate(cls, index, text, font, out_dir, height, extension, skewing_angle, random_skew, blur, random_blur, background_type, distorsion_type, distorsion_orientation, is_handwritten, name_format, text_color=-1, prefix = ""):
            image = None

            ##########################
            # Create picture of text #
            ##########################
            add_random_space = ' ' in text and decision(0.7)

            if add_random_space:
                text = add_random_space_to_string(text)

            height_inc = decision(0.05)
            tight_text = decision(0.2)

            if is_handwritten:
                image = HandwrittenTextGenerator.generate(text)
            else:
                image = ComputerTextGenerator.generate(text, font, text_color, height, random_height_inc=height_inc, tight_text=tight_text)

            random_angle = random.uniform(-skewing_angle, skewing_angle)

            rotated_img = image.convert('RGBA')
            rotated_img = rotated_img.rotate(skewing_angle if not random_skew else random_angle, expand=1) #.resize(image.size)
            white_mask = Image.new('RGBA', rotated_img.size, (255,) * 4)
            rotated_img = Image.composite(rotated_img, white_mask, rotated_img)
            rotated_img = rotated_img.convert('L')

            ###################################
            # Random miscellaneous distortion #
            ###################################

            if decision(0.3):
                if decision(0.7):
                    ## full image erode
                    x = random.randint(0, 1)
                    kernel = np.ones((x, x), np.uint8)
                    im_arr = cv2.erode(np.array(rotated_img), kernel, iterations=1)
                else:
                    ## partial image erode
                    im_arr = np.array(rotated_img)
                    start_x = random.randint(0, int(im_arr.shape[1] * 0.7))
                    if start_x + 10 < im_arr.shape[1]:
                        end_x = random.randint(start_x + 10, im_arr.shape[1])
                        x = random.randint(1, 3)
                        kernel = np.ones((x, x), np.uint8)
                        im_arr[:,start_x:end_x] = cv2.erode(im_arr[:,start_x:end_x], kernel, iterations=1)

                rotated_img = Image.fromarray(im_arr)

            # if (random.randint(0,10) < 3):
            #     x = random.randint(1,4)
            #     kernel = np.ones((x, x), np.uint8)
            #
            #     rotated_img = Image.fromarray(cv2.erode(np.array(rotated_img), kernel, iterations=1))
            # else:
            #     if (random.randint(0,10) < 1 and height > 45):
            #         x = random.randint(1, 4)
            #         kernel = np.ones((x, x), np.uint8)
            #
            #         rotated_img = Image.fromarray(cv2.morphologyEx(np.array(rotated_img), cv2.MORPH_CLOSE, kernel))
            #
            # f = random.uniform(0.9, 1.1)
            # if (random.randint(0, 1) == 0):
            #     rotated_img = rotated_img.resize((int(rotated_img.size[0] * f), int(rotated_img.size[1] * f)),
            #                                      Image.ANTIALIAS)
            # else:
            #     if (random.randint(0, 1) == 0):
            #         rotated_img = rotated_img.resize((int(rotated_img.size[0] * f), int(rotated_img.size[1] * f)),
            #                                          Image.BILINEAR)
            #     else:
            #         rotated_img = rotated_img.resize((int(rotated_img.size[0] * f), int(rotated_img.size[1] * f)),
            #                                          Image.LANCZOS)
            #
            # if (random.randint(0,30) < 1 and height > 60):
            #     rotated_img = Image.fromarray(nick_binarize([np.array(rotated_img)])[0])

            # if (random.randint(0,10) < 1 and height > 60):
            #     kernel = np.ones((2, 2), np.uint8)
            #
            #     rotated_img = Image.fromarray(cv2.morphologyEx(np.array(rotated_img), cv2.MORPH_TOPHAT, kernel))

            ######################################
            # Apply geometry distortion to image #
            ######################################

            distorsion_type = random.choice([0,1,2])
            if distorsion_type == 0:
                distorted_img = rotated_img # Mind = blown
            elif distorsion_type == 1:
                distorted_img = DistorsionGenerator.sin(
                    rotated_img,
                    vertical=(distorsion_orientation == 0 or distorsion_orientation == 2),
                    horizontal=(distorsion_orientation == 1 or distorsion_orientation == 2),
                    max_offset = 2
                )
            elif distorsion_type == 2:
                distorted_img = DistorsionGenerator.cos(
                    rotated_img,
                    vertical=(distorsion_orientation == 0 or distorsion_orientation == 2),
                    horizontal=(distorsion_orientation == 1 or distorsion_orientation == 2),
                    max_offset = 2
                )
            else:
                distorted_img = DistorsionGenerator.random(
                    rotated_img,
                    vertical=(distorsion_orientation == 0 or distorsion_orientation == 2),
                    horizontal=(distorsion_orientation == 1 or distorsion_orientation == 2)
                )

            affine_type = random.randint(0,4)
            if affine_type == 1:
                distorted_img = ElasticDistortionGenerator.afffine_transform(distorted_img)
            else:
                distorted_img = ElasticDistortionGenerator.elastic_transform(distorted_img)

            new_text_width, new_text_height = distorted_img.size

            x = random.randint(1, 10)
            y = random.randint(1, 10)

            #############################
            # Generate background image #
            #############################
            if (distorsion_type == 0):
                background_type = random.randint(0, 3)
            else:
                background_type = random.randint(0, 3)
            # background_type = 1

            if background_type == 0:
                background = BackgroundGenerator.gaussian_noise(new_text_height + x, new_text_width + y)
            elif background_type == 1:
                background = BackgroundGenerator.plain_white(new_text_height + x, new_text_width + y)
            elif background_type == 2:
                background = BackgroundGenerator.quasicrystal(new_text_height + x, new_text_width + y)
            else:
                background = BackgroundGenerator.picture(new_text_height + 10, new_text_width + 10)

            mask = distorted_img.point(lambda x: 0 if x == 255 or x == 0 else 255, '1')

            apply_background = False
            if (random.randint(0,10) < 1):
                background = distorted_img
            else:
                apply_background = True
                background.paste(distorted_img, (5, 5), mask=mask)

            ##################################
            # Resize image to desired format #
            ##################################
            new_width = float(new_text_width + y) * (float(height) / float(new_text_height + x))
            # image_on_background = background.resize((int(new_width), height), Image.ANTIALIAS)

            # if distorsion_type != 3 and background_type != 2 and new_text_height > 45:
            #     final_image = background.filter(
            #         ImageFilter.GaussianBlur(
            #             radius=(blur if not random_blur else random.randint(0, blur))
            #         )
            #     )
            # else:

            ##################################
            # Random motion blur             #
            ##################################
            final_image = background.convert('L')

            # blur distortion
            blur_type = random.randint(0,4)

            if blur_type == 1:
                final_image = RandomizedBlur(final_image)
            elif blur_type == 2:
                final_image = PsfBlur(final_image, 4)

            ## additional sharpening
            if decision(0.7):
                final_image = final_image.filter(ImageFilter.EDGE_ENHANCE)

            ##################################
            # Random aspect ration change    #
            ##################################
            f = random.uniform(0.7, 1.2)
            # if distorsion_type != 3:
            if (random.randint(0,1) == 0):
                final_image = final_image.resize((int(final_image.size[0] * f), int(final_image.size[1])), Image.ANTIALIAS)
            else:
                if (random.randint(0, 1) == 0):
                    final_image = final_image.resize((int(final_image.size[0]), int(final_image.size[1] * f)),
                                                 Image.BILINEAR)
                else:
                    final_image = final_image.resize((int(final_image.size[0]), int(final_image.size[1] * f)),
                                                     Image.LANCZOS)

            # final_image = Image.fromarray(nick_binarize([np.array(final_image)])[0])

            ## random binary if background is white
            if background_type == 1 and blur_type == 2 and decision(0.8) :
                final_image = Image.fromarray(sauvola_bin(final_image))

            # if (random.randint(0,10) < 3):
            # x = random.randint(0,1)
            # kernel = np.ones((x, x), np.uint8)
            #
            # final_image = Image.fromarray(cv2.erode(np.array(final_image), kernel, iterations=1))

            index += 1
            #####################################
            # Generate name for resulting image #
            #####################################
            if name_format == 0:
                image_name = '{}_{}.{}'.format(text, str(index), extension)
            elif name_format == 1:
                image_name = '{}_{}.{}'.format(str(index), text, extension)
            elif name_format == 2:
                image_name = '{}.{}'.format(str(index),extension)
            elif name_format == 3:
                image_name = '{}_{}.{}'.format(prefix, str(index), extension)
            else:
                print('{} is not a valid name format. Using default.'.format(name_format))
                image_name = '{}_{}.{}'.format(text, str(index), extension)

            print(image_name, font)
            # Save the image
            final_image.convert('L').save(os.path.join(out_dir, image_name))