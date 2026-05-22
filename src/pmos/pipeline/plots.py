"""Build chart-ready arrays from a (3, 1024) tensor for the dashboard.

Panels produced:
- time_domain         — raw waveforms per axis
- frequency_domain    — FFT magnitude spectrum per axis
- envelope_spectrum   — Hilbert envelope spectrum per axis (bearing-fault diagnostic)
- stats               — RMS, peak, crest factor, kurtosis per axis
"""
import numpy as np
from numpy.typing import NDArray
from scipy.signal import hilbert
from scipy.stats import kurtosis as _kurtosis

DEFAULT_SAMPLE_RATE_HZ = 50_000


def build_plot_data(tensor: NDArray, sample_rate_hz: int = DEFAULT_SAMPLE_RATE_HZ) -> dict:
    if tensor.ndim != 2 or tensor.shape[0] != 3:
        raise ValueError(f"expected tensor of shape (3, N), got {tensor.shape}")

    n_samples = tensor.shape[1]
    time_axis = (np.arange(n_samples) / sample_rate_hz).tolist()
    freq_axis = np.fft.rfftfreq(n_samples, 1.0 / sample_rate_hz).tolist()

    fft_mag = np.abs(np.fft.rfft(tensor, axis=1))
    env_mag = _envelope_spectrum(tensor)

    rms = np.sqrt(np.mean(tensor ** 2, axis=1))
    peak = np.max(np.abs(tensor), axis=1)
    crest = np.divide(peak, rms, out=np.zeros_like(peak), where=rms > 0)
    kurt = _kurtosis(tensor, axis=1, fisher=True)

    return {
        "time_domain": {
            "time_s": time_axis,
            "X": tensor[0].tolist(),
            "Y": tensor[1].tolist(),
            "Z": tensor[2].tolist(),
        },
        "frequency_domain": {
            "frequency_hz": freq_axis,
            "X": fft_mag[0].tolist(),
            "Y": fft_mag[1].tolist(),
            "Z": fft_mag[2].tolist(),
        },
        "envelope_spectrum": {
            "frequency_hz": freq_axis,
            "X": env_mag[0].tolist(),
            "Y": env_mag[1].tolist(),
            "Z": env_mag[2].tolist(),
        },
        "stats": {
            "rms": _axis_dict(rms),
            "peak": _axis_dict(peak),
            "crest_factor": _axis_dict(crest),
            "kurtosis": _axis_dict(kurt),
        },
    }


def _envelope_spectrum(tensor: NDArray) -> NDArray:
    analytic = hilbert(tensor, axis=-1)
    env = np.abs(analytic)
    env -= env.mean(axis=-1, keepdims=True)
    return np.abs(np.fft.rfft(env, axis=-1))


def _axis_dict(values: NDArray) -> dict:
    return {"X": float(values[0]), "Y": float(values[1]), "Z": float(values[2])}
