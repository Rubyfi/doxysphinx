# =====================================================================================
#  C O P Y R I G H T
# -------------------------------------------------------------------------------------
#  Copyright (c) 2022 by Robert Bosch GmbH. All rights reserved.
#
#  Author(s):
#  - Markus Braun, :em engineering methods AG (contracted by Robert Bosch GmbH)
#  - Celina Adelhardt, :em engineering methods AG (contracted by Robert Bosch GmbH)
# =====================================================================================

"""
Entry module for the doxysphinx cli.

Defines click main command (:func:`cli`) and subcommands (:func:`build`), (:func:`clean`)

.. note::
    * Execute this script directly to start doxysphinx.
    * If you need to call a function to start doxysphinx (e.g. for vscode launch config etc.) use the
      :func:`cli` directly.

        Sphinx autodoc which created this documentation seems to have problems with decorated methods.
        The function signatures shown here in the documentation aren't correct. Just click on view source to
        see the correct signatures.
"""

import logging
from pathlib import Path
from typing import Iterator, List

import click
import click_log  # type: ignore

from doxysphinx.doxygen import DoxygenSettingsValidator, read_doxyfile
from doxysphinx.process import Builder, Cleaner
from doxysphinx.utils.contexts import TimedContext

_logger = logging.getLogger()
click_log.basic_config(_logger)


@click.group()
@click.version_option()
@click_log.simple_verbosity_option(_logger)
def cli():
    """
    Integrates doxygen html documentation with sphinx.

    Doxysphinx typically should run right after doxygen. It will generate rst files out of doxygen's html
    files. This has the implication, that the doxygen html output directory (where the rst files are generated
    to) has to live inside sphinx's input tree.
    """
    click.secho("doxysphinx", fg="bright_white")


@cli.command()
@click.argument("sphinx_source", type=click.Path(file_okay=False, exists=True, path_type=Path))
@click.argument("sphinx_output", type=click.Path(file_okay=False, path_type=Path))
@click.argument("doxyfile", nargs=-1, type=click.Path(dir_okay=False, file_okay=True, exists=True, path_type=Path))
def build(doxyfile: List[Path], sphinx_source: Path, sphinx_output: Path):
    """
    Build rst and copy related files for doxygen projects.

    SPHINX_SOURCE specifies the root of the sphinx source directory tree while SPHINX_OUTPUT specifies the root of the
    sphinx output directory tree. The doxygen projects are specified through DOXYFILE (multiple possible).
    \f

    .. warning::

       * when using ``sphinx-build -b html SOURCE_DIR OUTPUT_DIR ...`` the html output will be put to ``OUTPUT_DIR`` so
         so doxysphinx's ``SPHINX_OUTPUT`` should be ``OUTPUT_DIR``.
       * when using ``sphinx-build -M html`` the html output will be put to ``OUTPUT_DIR/html`` so doxysphinx's
         ``SPHINX_OUTPUT`` should be ``OUTPUT_DIR/html``.
    """
    _logger.info("starting build command...")
    with TimedContext() as tc:
        doxygen_html_output_dirs = _read_and_validate_doxygen_config(doxyfile, sphinx_source)

        builder = Builder(sphinx_source, sphinx_output)
        for doxy_output in doxygen_html_output_dirs:
            builder.build(doxy_output)
    _logger.info(f"build command done in {tc.elapsed_humanized()}.")


@cli.command()
@click.argument("sphinx_source", type=click.Path(file_okay=False, exists=True, path_type=Path))
@click.argument("sphinx_output", type=click.Path(file_okay=False, path_type=Path))
@click.argument("doxyfile", nargs=-1, type=click.Path(dir_okay=False, file_okay=True, exists=True, path_type=Path))
def clean(doxyfile: List[Path], sphinx_source: Path, sphinx_output: Path):
    r"""
    Clean up files created by doxysphinx.

    SPHINX_SOURCE specifies the root of the sphinx source directory tree while SPHINX_OUTPUT specifies the root of the
    sphinx output directory tree. The doxygen projects are specified through DOXYFILE (multiple possible).
    """
    _logger.info("starting clean command...")
    with TimedContext() as tc:
        doxygen_html_output_dirs = _read_and_validate_doxygen_config(doxyfile, sphinx_source)

        cleaner = Cleaner(sphinx_source, sphinx_output)
        for doxy_output in doxygen_html_output_dirs:
            cleaner.cleanup(doxy_output)
    _logger.info(f"clean command done in {tc.elapsed_humanized()}.")


def _read_and_validate_doxygen_config(doxy_files: List[Path], sphinx_source: Path) -> Iterator[Path]:
    for doxy_file in doxy_files:
        config = read_doxyfile(doxy_file)
        # included_configs = get_included_configs(config)

        validator = DoxygenSettingsValidator()
        if not validator.validate(config, sphinx_source):
            if any(item for item in validator.validation_errors if not item.startswith("OPTIONAL")):
                message = validator.validation_msg
                raise click.UsageError(
                    f'The doxygen settings defined in "{doxy_file}"'
                    f"do not match the mandatory settings necessary for doxysphinx:\n"
                    f"{message}"
                )
            logging.warning("Not all optional doxygen settings are set correctly:\n")
            logging.warning(f"{validator.validation_msg}")

        yield validator.absolute_out


if __name__ == "__main__":
    cli()
