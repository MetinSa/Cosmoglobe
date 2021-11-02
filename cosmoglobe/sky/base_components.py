from abc import ABC, abstractmethod
from typing import Dict

from astropy.units import (
    Quantity,
    Unit,
    UnitConversionError,
    UnitsError,
    brightness_temperature,
    spectral,
)
import healpy as hp
import numpy as np

from cosmoglobe.sky._constants import DEFAULT_OUTPUT_UNIT, DEFAULT_FREQ_UNIT
from cosmoglobe.sky._exceptions import NsideError
from cosmoglobe.sky.components import SkyComponentLabel


class SkyComponent(ABC):
    """Abstract base class for sky components.

    Attributes
    ----------
    label
        Name of the sky component.
    amp
        Amplitude map.
    freq_ref
        Reference frequency of the amplitude map.
    spectral_parameters
        Dictionary containing the spectral parameters for the component.
    """

    label: SkyComponentLabel

    def __init__(
        self,
        amp: Quantity,
        freq_ref: Quantity,
        **spectral_parameters: Quantity,
    ):
        self.amp = amp
        self.freq_ref = freq_ref
        self.spectral_parameters = spectral_parameters

        self._validate_freq_ref(freq_ref)

    @staticmethod
    def _validate_freq_ref(freq_ref: Quantity):
        """Validates the type and shape of a reference frequency attribute."""

        if not isinstance(freq_ref, Quantity):
            raise TypeError("reference frequency must of type `astropy.units.Quantity`")

        if freq_ref.shape not in ((1, 1), (3, 1)):
            raise ValueError(
                "shape of reference frequency must be either (1, 1) or "
                "(3, 1) depending on if the component is polarized."
            )

        try:
            freq_ref.to(DEFAULT_FREQ_UNIT, equivalencies=spectral())
        except UnitConversionError:
            raise UnitsError(
                f"reference frequency must have units compatible with {DEFAULT_FREQ_UNIT}"
            )

    def __repr__(self) -> str:
        """Representation of the sky component."""

        main_repr = f"{self.__class__.__name__}"
        main_repr += "("
        extra_repr = ""
        for key in self.spectral_parameters.keys():
            extra_repr += f"{key}, "
        if extra_repr:
            extra_repr = extra_repr[:-2]
        main_repr += extra_repr
        main_repr += ")"

        return main_repr


class DiffuseComponent(SkyComponent):
    """Base class for diffuse sky components.

    A diffuse sky component must implement the `get_freq_scaling` method
    which computes the unscaled component SED.
    """

    def __init__(self, amp, freq_ref, **spectral_parameters):
        super().__init__(amp, freq_ref, **spectral_parameters)

        # The shapes of the attributes are critical to the sky simulation
        # which relies on broadcasting these quantities.
        self._validate_amp(amp)
        self._validate_spectral_parameters(spectral_parameters)

    @abstractmethod
    def get_freq_scaling(
        self, freqs: Quantity, **spectral_parameters: Quantity
    ) -> Quantity:
        """Computes and returns the frequency scaling factor.

        Parameters
        ----------
        freqs
            A frequency, or a list of frequencies for which to compute the
            scaling factor.
        **spectral_parameters
            The (unpacked) spectral parameters contained in the
            spectral_parameters dictionary for a given component.

        Returns
        -------
        scaling_factor
            The factor with which to scale the amplitude map for a set of
            frequencies.
        """

    def _validate_amp(self, amp: Quantity) -> None:
        if not isinstance(amp, Quantity):
            raise TypeError("ampltiude map must of type `astropy.units.Quantity`")

        try:
            hp.get_nside(amp)
        except TypeError:
            raise NsideError(
                f"the number of pixels ({amp.shape}) in the amplitude map "
                "does not correspond to a valid HEALPIX nside"
            )

        if self.freq_ref is not None:
            if amp.shape[0] != self.freq_ref.shape[0]:
                raise ValueError(
                    "shape of amplitude map must be either (1, `npix`) or "
                    "(3, `npix`) depending on if the component is polarized."
                )

            try:
                amp.to(
                    DEFAULT_OUTPUT_UNIT,
                    equivalencies=brightness_temperature(self.freq_ref),
                )
            except UnitConversionError:
                raise UnitsError(
                    f"amplitude map must have units compatible with {DEFAULT_OUTPUT_UNIT}"
                )

    def _validate_spectral_parameters(
        self, spectral_parameters: Dict[str, Quantity]
    ) -> None:
        for name, parameter in spectral_parameters.items():
            if not isinstance(parameter, Quantity):
                raise TypeError(
                    "spectral_parameter must be of type `astropy.units.Quantity`"
                )

            if parameter.ndim < 2 or parameter.shape[0] != self.amp.shape[0]:
                raise ValueError(
                    "shape of spectral parameter must be either (1, `npix`) or "
                    "(3, `npix`) if the parameter is a map, or (1, 1), (3, 1) "
                    "if the parameter is a scalar"
                )
            if parameter.shape[1] > 1:
                try:
                    hp.get_nside(parameter)
                except TypeError:
                    raise NsideError(
                        f"the number of pixels ({parameter.shape}) in the spectral "
                        f"parameter map {name} does not correspond to a valid "
                        "HEALPIX nside"
                    )


class PointSourceComponent(SkyComponent):
    """Base class for PointSource sky components.

    A pointsource sky component must implement the `get_freq_scaling` method
    which computes the unscaled component SED.

    Additionally, a catalog mapping each source to a coordinate given by
    latitude and longitude must be specificed as a class/instance attribute.
    """

    catalog: np.ndarray

    def __init__(self, amp, freq_ref, **spectral_parameters):
        super().__init__(amp, freq_ref, **spectral_parameters)

        # We validate the shape and type of the various class attributes.
        # The shapes of the attributes are critical to the sky simulation
        # which relies on broadcasting these quantities.
        self._validate_amp(amp)
        try:
            self._validate_catalog((self.catalog))
        except AttributeError:
            raise AttributeError(
                "a point source catalog must be specified as a class attribute."
            )
        self._validate_spectral_parameters(spectral_parameters)

    @abstractmethod
    def get_freq_scaling(
        self, freqs: Quantity, **spectral_parameters: Quantity
    ) -> Quantity:
        """Computes and returns the frequency scaling factor.

        Parameters
        ----------
        freqs
            A frequency, or a list of frequencies for which to compute the
            scaling factor.
        **spectral_parameters
            The (unpacked) spectral parameters contained in the
            spectral_parameters dictionary for a given component.

        Returns
        -------
        scaling_factor
            The factor with which to scale the amplitude map for a set of
            frequencies.
        """

    def _validate_amp(self, amp: Quantity) -> None:
        if not isinstance(amp, Quantity):
            raise TypeError("ampltiude map must of type `astropy.units.Quantity`")

        if amp.shape[0] != self.freq_ref.shape[0]:
            raise ValueError(
                "shape of amplitude map must be either (1, `npointsources`) or "
                "(3, `npointsources`) depending on if the component is polarized."
            )
        try:
            (amp / Unit("sr")).to(
                DEFAULT_OUTPUT_UNIT,
                equivalencies=brightness_temperature(self.freq_ref),
            )
        except UnitConversionError:
            raise UnitsError(
                "Radio sources must have units compatible with "
                f"{DEFAULT_OUTPUT_UNIT / Unit('sr')}"
            )

    def _validate_spectral_parameters(
        self, spectral_parameters: Dict[str, Quantity]
    ) -> None:
        for parameter in spectral_parameters.values():
            if not isinstance(parameter, Quantity):
                raise TypeError(
                    "spectral_parameter must be of type `astropy.units.Quantity`"
                )

            if parameter.ndim < 2 or parameter.shape[0] != self.amp.shape[0]:
                raise ValueError(
                    "shape of spectral parameter must be either (1, `npointsources`) or "
                    "(3, `npointsources`) if the parameter is a map, or (1, 1), (3, 1) "
                    "if the parameter is a scalar"
                )

    def _validate_catalog(self, catalog: np.ndarray):
        if catalog.shape[1] != self.amp.shape[1]:
            raise ValueError(
                f"number of pointsources ({self.amp.shape[1]}) does not "
                f"match the number of cataloged points ({self.catalog.shape}). "
                "catalog shape must be (3, `npointsources`)"
            )


class LineComponent(SkyComponent):
    """Base class for Line emission sky components.

    NOTE: This class is still in development, and no Line-emission components
    are currently implemented in Cosmoglobe.
    """

    def __init__(self, amp, freq_ref, **spectral_parameters):
        super().__init__(amp, freq_ref, **spectral_parameters)

        self._validate_amp(amp)

    def _validate_amp(self, value: Quantity) -> None:
        if not isinstance(value, Quantity):
            raise TypeError("ampltiude map must of type `astropy.units.Quantity`")

        if value.shape[0] != self.freq_ref.shape[0]:
            raise ValueError(
                "shape of amplitude map must be either (1, `npointsources`) or "
                "(3, `npointsources`) depending on if the component is polarized."
            )

        try:
            (value / Unit("km/s")).to(
                DEFAULT_OUTPUT_UNIT,
                equivalencies=brightness_temperature(self.freq_ref),
            )
        except UnitConversionError:
            raise UnitsError(
                "amplitude map must have units compatible with "
                f"{DEFAULT_OUTPUT_UNIT / Unit('km/s')}"
            )
