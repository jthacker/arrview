import colorsys


def color_generator(hue_start=0, saturation=1, lightness=0.5):
    """Generator that returns colors sampled from HSL color space
    Each successive color is sample at the golden ratio from the previous
    color in hue. Saturation and value are fixed at instantiation

    Parameters
    ----------
    hue_start : float
        starting hue value
    saturation : float
        fixed 'saturation' value between 0 and 1
    lightness : float
        fixed 'lightness' value between 0 and 1

    Returns
    -------
    Generator of RGB tuples
    """
    assert 0 <= hue_start <= 1
    assert 0 <= saturation <= 1
    assert 0 <= lightness <= 1
    hue = hue_start
    golden_ratio_conjugate = (1 - 5**0.5) / 2
    while True:
        yield colorsys.hls_to_rgb(hue, lightness, saturation)
        hue = (hue + golden_ratio_conjugate) % 1
