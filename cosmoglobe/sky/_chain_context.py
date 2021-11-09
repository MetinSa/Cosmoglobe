from typing import Dict, Protocol

from astropy.units import Quantity, Unit
import numpy as np

from cosmoglobe.sky._context_registry import ChainContextRegistry
from cosmoglobe.sky.components.ame import AME
from cosmoglobe.sky.components.cmb import CMB
from cosmoglobe.sky.components.dust import ThermalDust
from cosmoglobe.sky.components.freefree import FreeFree
from cosmoglobe.sky.components.radio import Radio
from cosmoglobe.sky.components.synchrotron import Synchrotron


class ChainContext(Protocol):
    """Protocol defining context for chain files.

    Chain context defines additional processing required on the chain items
    before they are ready to be put into the sky model.
    """

    def __call__(self, args: Dict[str, Quantity]) -> Dict[str, Quantity]:
        """Function that performs the processing on the specific chain item.

        This function needs to manipulate and return the `args` dictionary
        """


class FreqRefContext:
    """Re-shapes freq_ref for unpolarized components."""

    def __call__(self, args: Dict[str, Quantity]) -> Dict[str, Quantity]:
        if "freq_ref" in args:
            args["freq_ref"] = args["freq_ref"].to("GHz")
            if (amp_dim := args["amp"].shape[0]) == 1:
                args["freq_ref"] = args["freq_ref"][0].reshape((1, 1))
            elif amp_dim == 3:
                args["freq_ref"] = args["freq_ref"].reshape((3, 1))
            else:
                raise ValueError("cannot reshape freq_ref into shape (3,1) or (1,1")
        return args


class RadioContext:
    """Context for the radio component in the chain.

    In the chain, the amp of radio is stored in units of 'mJy'. Here we
    manually set convert it to 'uK' through astropy.

    NOTE: we pretend that amp has units of 'mJy/sr' to be able convert
    the units properly. This is fine since we always end dividing by
    the beam_area when converting the amplitudes to HEALPIX maps.

    """

    def __call__(self, args: Dict[str, Quantity]) -> Dict[str, Quantity]:
        args["alpha"] = args["alpha"][0]

        return args


class MapToScalarContext:
    """Extract and returns a scalar.

    Datasets in the cosmoglobe chains tends to be stored in HEALPIX maps.
    A quantity is considered a scalar if it is constant over all axes of the
    dataset.
    """

    def __call__(self, args: Dict[str, Quantity]) -> Dict[str, Quantity]:
        IGNORED_ARGS = ["amp", "freq_ref"]
        for key, value in args.items():
            if key not in IGNORED_ARGS and np.size(value) > 1:
                if np.ndim(value) > 1:
                    uniques = [np.unique(col) for col in value]
                    all_cols_are_unique = all([len(col) == 1 for col in uniques])
                else:
                    uniques = np.unique(value)
                    all_cols_are_unique = len(uniques) == 1

                if all_cols_are_unique:
                    args[key] = Quantity(uniques, unit=value.unit)

        return args


chain_context_registry = ChainContextRegistry()

chain_context_registry.register_context([], FreqRefContext)
chain_context_registry.register_context([], MapToScalarContext)
chain_context_registry.register_context([Radio], RadioContext)

chain_context_registry.register_mapping([], {"freq_ref": "nu_ref"})
chain_context_registry.register_mapping([Radio], {"alpha": "specind"})
chain_context_registry.register_mapping([AME], {"freq_peak": "nu_p"})
chain_context_registry.register_mapping([FreeFree], {"T_e": "Te"})

chain_context_registry.register_units([], {"freq_ref": Unit("Hz")})
chain_context_registry.register_units(
    [AME, ThermalDust, Synchrotron, FreeFree], {"amp": Unit("uK_RJ")}
)
chain_context_registry.register_units([CMB], {"amp": Unit("uK_CMB")})
chain_context_registry.register_units([Radio], {"amp": Unit("mJy")})
chain_context_registry.register_units([AME], {"freq_peak": Unit("GHz")})
chain_context_registry.register_units([ThermalDust], {"T": Unit("K")})
chain_context_registry.register_units([FreeFree], {"T_e": Unit("K")})
