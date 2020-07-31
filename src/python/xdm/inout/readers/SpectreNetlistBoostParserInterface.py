#-------------------------------------------------------------------------
#   Copyright 2002-2020 National Technology & Engineering Solutions of
#   Sandia, LLC (NTESS).  Under the terms of Contract DE-NA0003525 with
#   NTESS, the U.S. Government retains certain rights in this software.
#
#   This file is part of the Xyce(TM) XDM Netlist Translator.
#   
#   Xyce(TM) XDM is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#  
#   Xyce(TM) XDM is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#   
#   You should have received a copy of the GNU General Public License
#   along with the Xyce(TM) XDM Netlist Translator.
#   If not, see <http://www.gnu.org/licenses/>.
#-------------------------------------------------------------------------

import logging
import os
import re
import sys

import SpiritCommon
import SpectreSpirit

from xdm import Types
from xdm.inout.readers import BoostParserInterface
from xdm.inout.readers.ParsedNetlistLine import ParsedNetlistLine

spectre_to_adm_model_type_map = {"resistor": "R", "capacitor": "C", "diode": "D", "inductor": "L",
                                 "mutual_inductor": "K", "gaas": "Z", "tline": "T", "vcvs": "E", "vccs": "G",
                                 "pvcvs": "E", "pvccs": "G", "vsource": "V", "isource": "I", "jfet": "J", "mos1": "M",
                                 "bsim3v3": "M", "mos902": "M", "bsimsoi": "M", "model": ".MODEL", "parameters": ".PARAM",
                                 "bjt": "Q", "vbic": "Q",
                                 "subckt": ".SUBCKT", "ends": ".ENDS", "include": ".INCLUDE", "section": ".LIB",
                                 "endsection": ".ENDL", "ac": "ac", "alter": "alter", "altergroup": "altergroup",
                                 "check": "check", "checklimit": "checklimit", "cosim": "cosim", "dc": "dc",
                                 "dcmatch": "dcmatch", "envlp": "envlp", "hb": "hb", "hbac": "hbac",
                                 "hbnoise": "hbnoise", "hbsp": "hbsp", "info": "info", "loadpull": "loadpull",
                                 "montecarlo": "montecarlo", "noise": "noise", "options": "options", "pac": "pac",
                                 "pdisto": "pdisto", "pnoise": "pnoise", "psp": "psp", "pss": "pss", "pstb": "pstb",
                                 "pxf": "pxf", "pz": "pz", "qpac": "qpac", "qpnoise": "qpnoise", "qpsp": "qpsp",
                                 "qpss": "qpss", "qpxf": "qpxf", "reliability": "reliability", "set": "set",
                                 "shell": "shell", "sp": "sp", "stb": "stb", "sweep": "sweep", "tdr": "tdr",
                                 "tran": ".TRAN", "uti": "uti", "xf": "xf", "analogmodel": "analogmodel",
                                 "bsource": "bsource", "checkpoint": "checkpoint", "smiconfig": "smiconfig",
                                 "constants": "constants", "convergence": "convergence", "encryption": "encryption",
                                 "expressions": "expressions", "functions": "functions", "global": "global",
                                 "ibis": "ibis", "ic": "ic", "if": "if", "keywords": "keywords", "memory": "memory",
                                 "nodeset": "nodeset", "param_limits": "param_limits", "paramset": "paramset",
                                 "rfmemory": "rfmemory", "save": ".PRINT", "savestate": "savestate", "sens": "sens",
                                 "spectrerf": "spectrerf", "stitch": "stitch", "vector": "vector",
                                 "veriloga": "veriloga", "simulator": "simulator", "library": "library",
                                 "endlibrary": "endlibrary", "modelParameter": "modelParameter",
                                 "simulatorOptions": "simulatorOptions", "finalTimeOP": "finalTimeOP",
                                 "element": "element", "outputParameter": "outputParameter",
                                 "designParamVals": "designParamVals", "primitives": "primitives", "subckts": "subckts",
                                 "saveOptions": "saveOptions"}

spectre_tran_param_type = {
    "step": Types.printStepValue,
    "stop": Types.finalTimeValue
}

def format_output_variable(input_string):
    result = input_string
    if "(" not in input_string:
        if ":1" in input_string:
            result = "I(" + input_string + ")"
            result = result.replace(":1", "")
        else:
            result = "V(" + input_string + ")"

    if "{" not in result:
        result = result.replace(".", ":")
    return result


def is_a_number(expression):
    try:
        float(expression)
        return True
    except ValueError:
        return False


def convert_to_xyce(expression):
    """
    split on anything we want to convert or identify as legal or illegal
    in Xyce. If a token is illegal it should raise an warning in XDM. If a token
    is legal in Xyce then the expression that contains it should be surrounded
    by {}. If a token is converted to something legal in Xyce, then it the
    expression that contains it should be surrounded by {}. msg should be set
    to the warning message, if any, and that should trigger a
    logging.warning(...) call. This call is up to the caller of this functions.
    """
    # Only set msg if there's an error
    msg = ""

    # Split the expression string by all tokens we want to examine for validity
    # or conversion to Xyce, and whether that token makes the input an
    # expression which requires {}
    # ? identifies the ternary operator which is valid in Spectre but not
    # in Xyce.
    tokens = (
        "(\+|-|\*\*|\*|\/|&&|&|==|<<|<|>>|>|<=|>=|\|\||\||M_PI_4|M_PI_2|M_PI|M_1_PI|M_2_PI|M_TWO_PI|M_2_SQRTPI|M_SQRT1_2|M_SQRT2|M_DEGPERRAD|M_E|M_LN10|M_LN2|M_LOG10E|M_LOG2E|P_C|P_H|P_K|P_Q|log|log10|exp|sqrt|min|max|abs|pow|int|hypot|ceil|floor|fmod|acosh|acos|asinh|asin|atan2|atanh|atan|cosh|cos|sinh|sin|tanh|tan|\?|:)")
    split = re.split(tokens, expression.replace(" ", ""))

    # convert Spectre boolean operators to their Xyce counterparts
    # convert Spectre functions to uppercase
    # convert spectre constants to numeric values
    spectre_to_xyce = {"M_PI_4": "0.78539816339744830962", "M_PI_2": "1.57079632679489661923",
                       "M_PI": "3.14159265358979323846", "M_1_PI": "0.31830988618379067154",
                       "M_2_PI": "0.63661977236758134308", "M_2_SQRTPI": "1.12837916709551257390",
                       "M_DEGPERRAD": "57.2957795130823208772", "M_E": "2.7182818284590452354",
                       "M_LN10": "2.30258509299404568402", "M_LN2": "0.69314718055994530942",
                       "M_LOG10E": "0.43429448190325182765", "M_LOG2E": "1.4426950408889634074",
                       "M_SQRT1_2": "0.70710678118654752440", "M_SQRT2": "1.4142135623730950488",
                       "M_TWO_PI": "6.28318530717958647652", "P_C": "2.997924562e8", "P_H": "6.6260755e-34",
                       "P_K": "1.3806226e-23", "P_Q": "1.6021918e-19", "||": "|", "&&": "&", "<<": "<", ">>": ">",
                       "log": "LOG", "log10": "LOG10", "exp": "EXP", "sqrt": "SQRT", "min": "MIN", "max": "MAX",
                       "abs": "ABS", "pow": "POW", "int": "INT", "sin": "SIN", "tanh": "TANH", "tan": "TAN",
                       "sinh": "SINH", "cosh": "COSH", "cos": "COS", "atanh": "ATANH", "atan2": "ATAN2", "atan": "ATAN",
                       "asinh": "ASINH", "asin": "ASIN", "acosh": "ACOSH", "acos": "ACOS"}

    # Is this a Xyce expression?
    # The occurance of any of these list membbers indicates that we have
    # an expression that needs to be surrounded by {}
    valid_xyce_ops = ["+", "-", "**", "*", "/", "~", "|", "&", "==", "!=", ">", ">=", ">", ">="]
    # These are invalid in Xyce
    # invalid_ops = ["&", "|", "~^", "^~"]

    # These functions aren't available in Xyce
    # invalid_ftns = ["hypot", "ceil", "floor", "fmod", "?"]
    needs_parens = False
    for i, token in enumerate(split):
        # Find things that can't be converted to xyce
        # These are currently caught by the boost parser
        # if token in invalid_ops:
        # msg = "Spectre expression constaints bitwise operator " + token + " not available in Xyce."
        # return None, msg
        # Find things that can't be converted to xyce
        # These are currently caught by the boost parser
        # if token in invalid_ftns:
        # msg = "Spectre expression contains function" + token + " not available in Xyce."
        # return None, msg

        # convert what we can
        # id = spectre_tran_param_type
        if token in spectre_to_xyce:
            split[i] = spectre_to_xyce[token]
        if token in valid_xyce_ops:
            needs_parens = True

    # Once the parser stops blocking the ternary operator, this will convert it to the
    # IF(x,x,x) command in Xyce
    # Convert the ternary operator in Spectre to the IF(bool,value,value)
    # in Xyce
    # if "?" in split and ":" in split:
    # ternary_id1 = split.index("?")
    # ternary_id2 = split.index(":")
    # if len(split) > ternary_id2 + 1 and ternary_id2 == ternary_id1 + 2:
    # split[ternary_id] = "IF("
    # split[ternary_id-1] + ","
    # split[ternary_id+1] + ","
    # split[ternary_id+3] + ")"
    # del(split[ternary_id-1])
    # del(split[ternary_id+1])
    # del(split[ternary_id+2])

    if needs_parens:
        return "{" + "".join(split) + "}", msg
    else:
        return "".join(split), msg


class SpectreNetlistBoostParserInterface(object):
    """
    Allows for Spectre to be read in using the Boost Parser.  Iterates over
    statements within the Spectre netlist file.
    """

    def __init__(self, filename, language_definition, top_level_file=True):
        self.internal_parser = SpectreSpirit.SpectreNetlistBoostParser()
        self.goodfile = self.internal_parser.open(filename, top_level_file)
        self.line_iter = iter(self.internal_parser)
        self._filename = filename
        self._language_definition = language_definition
        self._top_level_file = top_level_file

        if not self.goodfile:
            logging.error("File: " + filename + " was not found. Please locate this file and try again.\n\n\n")
            sys.exit(1)

        # a list of parsed netlist line objects created during conversion to adm
        self._synthesized_pnls = []

    def __del__(self):
        self.internal_parser.close()

    def __iter__(self):
        return self

    def __next__(self, silent=False):
        """
        Iterates over parsed line, which is a collection of parsed objects
        """

        boost_parsed_line = next(self.line_iter)

        pnl = ParsedNetlistLine(boost_parsed_line.filename, boost_parsed_line.linenums)

        parsed_object_iter = iter(boost_parsed_line.parsed_objects)

        for parsedObject in parsed_object_iter:
            self.convert_next_token(parsedObject, parsed_object_iter, pnl, self._synthesized_pnls)

        if len(pnl.source_params) > 0:
            self._handle_source_params(pnl)

        if not silent:
            if boost_parsed_line.error_type == "critical":
                pnl.error_type = boost_parsed_line.error_type
                pnl.error_message = boost_parsed_line.error_message
                logging.critical("In file:\"" + str(os.path.basename(pnl.filename)) + "\" at line:" + str(
                    pnl.linenum) + ". " + boost_parsed_line.error_message)
            elif boost_parsed_line.error_type == "error":
                pnl.error_type = boost_parsed_line.error_type
                pnl.error_message = boost_parsed_line.error_message
                logging.error("In file:\"" + str(os.path.basename(pnl.filename)) + "\" at line:" + str(
                    pnl.linenum) + ". " + boost_parsed_line.error_message)
            elif boost_parsed_line.error_type == "warn":
                pnl.error_type = boost_parsed_line.error_type
                pnl.error_message = boost_parsed_line.error_message
                logging.warning("In file:\"" + str(os.path.basename(pnl.filename)) + "\" at line:" + str(
                    pnl.linenum) + ". " + boost_parsed_line.error_message)
            elif boost_parsed_line.error_type == "info":
                pnl.error_type = boost_parsed_line.error_type
                pnl.error_message = boost_parsed_line.error_message
                logging.info("In file:\"" + str(os.path.basename(pnl.filename)) + "\" at line:" + str(
                    pnl.linenum) + ". " + boost_parsed_line.error_message)
            else:
                pnl.error_type = " "

        return pnl

    @staticmethod
    def _handle_source_params(pnl):
        """
        Maps known source params to appropriate transient types
        """
        if pnl.source_params.get("type"):
            if pnl.source_params["type"] == "dc" and pnl.source_params.get("dc") and pnl.source_params["dc"] != "0":
                pnl.add_known_object(pnl.source_params["dc"], Types.dcValueValue)

            elif pnl.source_params["type"] == "sine":
                pnl.add_known_object("SIN", Types.trans_func)
                if pnl.source_params.get("sinedc"):
                    pnl.add_transient_value(pnl.source_params["sinedc"])
                else:
                    pnl.add_transient_value("0")
                if pnl.source_params.get("ampl"):
                    pnl.add_transient_value(pnl.source_params["ampl"])
                else:
                    pnl.add_transient_value("1")
                if pnl.source_params.get("freq"):
                    pnl.add_transient_value(pnl.source_params["freq"])
                else:
                    pnl.add_transient_value("0")
                if pnl.source_params.get("delay"):
                    pnl.add_transient_value(pnl.source_params["delay"])
                else:
                    pnl.add_transient_value("0")
                if pnl.source_params.get("damp"):
                    pnl.add_transient_value(pnl.source_params["damp"])
                else:
                    pnl.add_transient_value("0")
                if pnl.source_params.get("phase"):
                    pnl.add_transient_value(pnl.source_params["phase"])
                else:
                    pnl.add_transient_value("0")

            elif pnl.source_params["type"] == "exp":
                pnl.add_known_object("EXP", Types.trans_func)
                if pnl.source_params.get("val0"):
                    pnl.add_transient_value(pnl.source_params["val0"])
                else:
                    pnl.add_transient_value("0")
                if pnl.source_params.get("val1"):
                    pnl.add_transient_value(pnl.source_params["val1"])
                else:
                    pnl.add_transient_value("1")
                if pnl.source_params.get("td1"):
                    pnl.add_transient_value(pnl.source_params["td1"])
                else:
                    pnl.add_transient_value("0")
                if pnl.source_params.get("tau1"):
                    pnl.add_transient_value(pnl.source_params["tau1"])
                else:
                    pnl.add_transient_value("0")
                if pnl.source_params.get("td2"):
                    pnl.add_transient_value(pnl.source_params["td2"])
                else:
                    pnl.add_transient_value("0")
                if pnl.source_params.get("tau2"):
                    pnl.add_transient_value(pnl.source_params["tau2"])
                else:
                    pnl.add_transient_value("0")

            elif pnl.source_params["type"] == "pulse":
                pnl.add_known_object("PULSE", Types.trans_func)
                if pnl.source_params.get("val0"):
                    pnl.add_transient_value(pnl.source_params["val0"])
                else:
                    pnl.add_transient_value("0")
                if pnl.source_params.get("val1"):
                    pnl.add_transient_value(pnl.source_params["val1"])
                else:
                    pnl.add_transient_value("1")
                if pnl.source_params.get("delay"):
                    pnl.add_transient_value(pnl.source_params["delay"])
                else:
                    pnl.add_transient_value("0")
                if pnl.source_params.get("rise"):
                    pnl.add_transient_value(pnl.source_params["rise"])
                else:
                    pnl.add_transient_value("0")
                if pnl.source_params.get("fall"):
                    pnl.add_transient_value(pnl.source_params["fall"])
                else:
                    pnl.add_transient_value("0")
                if pnl.source_params.get("width"):
                    pnl.add_transient_value(pnl.source_params["width"])
                else:
                    pnl.add_transient_value("0")
                if pnl.source_params.get("period"):
                    pnl.add_transient_value(pnl.source_params["period"])
                else:
                    pnl.add_transient_value("0")

            elif pnl.source_params["type"] == "pwl":
                pnl.add_known_object("PWL", Types.trans_func)
                if pnl.source_params.get("file"):
                    pnl.add_transient_value("FILE")
                    pnl.add_transient_value(pnl.source_params["file"])
                if pnl.source_params.get("delay"):
                    pnl.add_param_value_pair("delay", pnl.source_params["delay"])

        # For cases where the optional "type" parameter isn't specified
        elif pnl.source_params.get("dc"):
            pnl.add_known_object(pnl.source_params["dc"], Types.dcValueValue)

        # source_params_deleted = {"type", "dc", "sinedc", "ampl", "freq", "delay", "damp", "phase", "val0", "val1",
        #                          "td1", "tau1", "td2", "tau2", "rise", "fall", "width", "period", "file" }
        # for key in source_params_deleted:
        #     if key in self._source_params:
        #         del self._source_params[key]
        #
        # for key, value in self._source_params.iteritems():
        #     pnl.add_param_value_pair(key, value)

    @staticmethod
    def set_tran_param(pnl, param_key, param_value):
        """
        Maps known tran params
        """
        if spectre_tran_param_type.get(param_key):
            if not param_value.endswith("s"):
                param_value = param_value + "s"
            pnl.add_known_object(param_value, spectre_tran_param_type[param_key])
        else:
            logging.warning(
                "Unsupported parameter in spectre tran statement: " + param_key + " Line(s): " + str(pnl.linenum))

    def convert_next_token(self, parsed_object, parsed_object_iter, pnl, synthesized_pnls):
        """
        Takes individual parsed objects from the parsed line object

        Populate ParsedNetlistLine class with all information necessary to create a Statement

        Many hacks contained here
        """
        if parsed_object.types[0] == SpiritCommon.data_model_type.DIRECTIVE_NAME and parsed_object.value.upper() == "DC":
            pnl.type = ".DC"

        elif parsed_object.types[0] == SpiritCommon.data_model_type.DIRECTIVE_NAME or parsed_object.types[
            0] == SpiritCommon.data_model_type.DEVICE_TYPE:
            if spectre_to_adm_model_type_map.get(parsed_object.value):
                pnl.type = spectre_to_adm_model_type_map[parsed_object.value]
                pnl.local_type = parsed_object.value
            else:
                logging.warning("Possible error. Spectre type not recognized: " + str(parsed_object.value))

        elif parsed_object.types[0] == SpiritCommon.data_model_type.MODEL_NAME and not pnl.type == ".MODEL":
            if spectre_to_adm_model_type_map.get(parsed_object.value):
                pnl.type = spectre_to_adm_model_type_map[parsed_object.value]
                pnl.local_type = parsed_object.value
            else:
                pnl.add_known_object(parsed_object.value, Types.modelName)

        elif parsed_object.types[0] == SpiritCommon.data_model_type.MODEL_TYPE and pnl.type == ".MODEL":
            adm_type = spectre_to_adm_model_type_map.get(parsed_object.value)

            # For Spectre, different models aren't distinguished by a "LEVEL" parameter. Instead,
            # it uses a name to distinguish what model is being used (ex., bsimsoi instead of
            # LEVEL=10, or vbic instead of LEVEL=10).
            if adm_type == "M" or adm_type == "Q" or adm_type == "J":
                pnl.add_param_value_pair("LEVEL", parsed_object.value)

            if not adm_type:
                adm_type = parsed_object.value


            # Default to NMOS for type
            if adm_type == "M":
                pnl.add_known_object("NMOS", Types.modelType)
                pnl.add_param_value_pair("type", "N")
            elif adm_type == "J":
                pnl.add_known_object("NJF", Types.modelType)
                pnl.add_param_value_pair("type", "N")
            else:
                pnl.add_known_object(adm_type, Types.modelType)

        elif parsed_object.types[0] == SpiritCommon.data_model_type.DEVICE_NAME or (
                parsed_object.types[0] == SpiritCommon.data_model_type.MODEL_NAME and pnl.type == ".MODEL"):
            pnl.name = parsed_object.value

        elif parsed_object.types[0] == SpiritCommon.data_model_type.PARAM_NAME and (pnl.type == ".DC" or pnl.type == ".AC"):
            # .DC and .AC directives need four PARAM_NAME/PARAM_VALUE pairs - a sweep variable name,
            # a start value, a stop value, and a step value
            sweep_list = ["", "", "", ""]
            sweep_parsed_object = parsed_object

            for i in range(8):
                if sweep_parsed_object.types[0] == SpiritCommon.data_model_type.PARAM_NAME and sweep_parsed_object.value.lower() in ["dev", "param"]:
                    sweep_index = 0
                    if sweep_parsed_object.value.lower() == "dev":
                        pnl.flag_unresolved_device = True
                elif sweep_parsed_object.types[0] == SpiritCommon.data_model_type.PARAM_NAME and sweep_parsed_object.value.lower() == "start":
                    sweep_index = 1
                elif sweep_parsed_object.types[0] == SpiritCommon.data_model_type.PARAM_NAME and sweep_parsed_object.value.lower() == "stop":
                    sweep_index = 2
                elif sweep_parsed_object.types[0] == SpiritCommon.data_model_type.PARAM_NAME and sweep_parsed_object.value.lower() == "step":
                    sweep_index = 3

                if sweep_parsed_object.types[0] == SpiritCommon.data_model_type.PARAM_VALUE:
                    sweep_list[sweep_index] = sweep_parsed_object.value

                # make sure not to iterate anymore on the last PARAM_VALUE or it will cause problems
                # with further parsing
                if i < 7:
                    sweep_parsed_object = next(parsed_object_iter)

                if not (sweep_parsed_object.types[0] == SpiritCommon.data_model_type.PARAM_VALUE or sweep_parsed_object.types[0] == SpiritCommon.data_model_type.PARAM_NAME):
                    logging.error(
                        "Line(s):" + str(pnl.linenum) + ". Parser passed wrong token.  Expected PARAM_VALUE.  Got " + str(
                            sweep_parsed_object.types[0]))
                    raise Exception("Next Token is not a PARAM_VALUE.  Something went wrong!")

            for sweep_item in sweep_list:
                pnl.add_sweep_param_value(sweep_item)

        elif parsed_object.types[0] == SpiritCommon.data_model_type.PARAM_NAME:
            # For Spectre, the polarity of the device (ex. NMOS or PMOS, or NPN or PNP) 
            # isn't declared as a separate identifier in the .MODEL statement. Instead, 
            # it is saved as a model parameter called "type". The polarity needs to be
            # extracted and saved in the data model consistent with SPICE parsing
            if pnl.type == ".MODEL" and parsed_object.value.upper() == "TYPE":
                param_value_parsed_object = next(parsed_object_iter)

                if pnl.known_objects.get(Types.modelType).endswith("MOS"):
                    pnl.add_known_object(param_value_parsed_object.value.upper()+"MOS", Types.modelType)
                elif pnl.known_objects.get(Types.modelType).endswith("JF"):
                    pnl.add_known_object(param_value_parsed_object.value.upper()+"JF", Types.modelType)
                else:
                    pnl.add_known_object(param_value_parsed_object.value, Types.modelType)

                pnl.add_param_value_pair(parsed_object.value, param_value_parsed_object.value)

            elif pnl.type == ".MODEL" and parsed_object.value.upper() == "VERSION":
                param_value_parsed_object = next(parsed_object_iter)
                pnl.add_param_value_pair(parsed_object.value.upper(), param_value_parsed_object.value)

            elif not parsed_object.value == "wave":
                param_value_parsed_object = next(parsed_object_iter)

                if pnl.type and pnl.type == ".TRAN":
                    self.set_tran_param(pnl, parsed_object.value, param_value_parsed_object.value)

                elif pnl.type and pnl.type == "V" or pnl.type == "I":
                    pnl.source_params[parsed_object.value] = param_value_parsed_object.value

                else:
                    if param_value_parsed_object.types[0] != SpiritCommon.data_model_type.PARAM_VALUE:
                        raise Exception("Next Token is not a PARAM_VALUE.  Something went wrong!")

                    if (parsed_object.value.upper() == "M") and pnl.type not in ['R', 'L', 'C']:
                        pnl.m_param = param_value_parsed_object.value

                    msg = None
                    # expression = None
                    if param_value_parsed_object.value.startswith('[') and param_value_parsed_object.value.endswith(
                            ']'):
                        expression = param_value_parsed_object.value
                    elif is_a_number(param_value_parsed_object.value):
                        expression = param_value_parsed_object.value
                    else:
                        expression, msg = convert_to_xyce(param_value_parsed_object.value)

                    if expression:
                        pnl.add_param_value_pair(parsed_object.value, expression)
                    else:
                        pnl.add_param_value_pair(parsed_object.value, param_value_parsed_object.value)

                    if msg:
                        logging.warning("Error in expression: " + msg + str(parsed_object.value))

        elif parsed_object.types[0] == SpiritCommon.data_model_type.CONTROL_DEVICE:

            control_dev_name_obj = next(parsed_object_iter)

            if control_dev_name_obj.types[0] != SpiritCommon.data_model_type.CONTROL_DEVICE_NAME:
                raise Exception("Next Token is not a CONTROL_DEVICE_NAME.  Something went wrong!")

            pnl.add_control_param_value(parsed_object.value + control_dev_name_obj.value)

        elif parsed_object.types[0] == SpiritCommon.data_model_type.SWEEP_PARAM_VALUE:

            pnl.add_sweep_param_value(parsed_object.value)

        elif parsed_object.types[0] == SpiritCommon.data_model_type.SCHEDULE_PARAM_VALUE:

            pnl.add_schedule_param_value(parsed_object.value)

        elif parsed_object.types[0] == SpiritCommon.data_model_type.LIST_PARAM_VALUE:

            pnl.add_value_to_value_list(parsed_object.value)

        elif parsed_object.types[0] == SpiritCommon.data_model_type.TABLE_PARAM_VALUE:

            pnl.add_table_param_value(parsed_object.value)

        elif parsed_object.types[0] == SpiritCommon.data_model_type.POLY_PARAM_VALUE:

            pnl.add_poly_param_value(parsed_object.value)

        elif parsed_object.types[0] == SpiritCommon.data_model_type.CONTROL_PARAM_VALUE:

            pnl.add_control_param_value(parsed_object.value)

        elif parsed_object.types[0] == SpiritCommon.data_model_type.SUBCKT_DIRECTIVE_PARAM_VALUE:

            pnl.add_subckt_directive_param_value(parsed_object.value)

        elif parsed_object.types[0] == SpiritCommon.data_model_type.SUBCKT_DEVICE_PARAM_VALUE:

            pnl.add_subckt_device_param_value(parsed_object.value)

        elif parsed_object.types[0] == SpiritCommon.data_model_type.TRANS_REF_NAME:
            pnl.add_transient_value(parsed_object.value)

        elif parsed_object.types[0] == SpiritCommon.data_model_type.OUTPUT_VARIABLE:
            formatted_output_variable = format_output_variable(parsed_object.value)
            pnl.add_output_variable_value(formatted_output_variable)

        elif parsed_object.types[0] == SpiritCommon.data_model_type.FUNC_ARG_VALUE:
            pnl.add_func_arg_value(parsed_object.value)

        elif parsed_object.types[0] == SpiritCommon.data_model_type.INLINE_COMMENT:
            pnl.add_inline_comment(parsed_object.value)

        elif parsed_object.types[0] == SpiritCommon.data_model_type.UNKNOWN_NODE:
            pnl.add_unknown_node(parsed_object.value)

        elif parsed_object.types[0] == SpiritCommon.data_model_type.TITLE:
            pnl.type = "TITLE"
            pnl.name = parsed_object.value
            pnl.add_comment(parsed_object.value)

        elif parsed_object.types[0] == SpiritCommon.data_model_type.COMMENT:
            pnl.type = "COMMENT"
            pnl.name = parsed_object.value
            pnl.add_comment(parsed_object.value)

        elif len(parsed_object.types) == 1:
            # convert to .lib from .include
            if parsed_object.types[
                0] == SpiritCommon.data_model_type.LIB_ENTRY and pnl.type and not pnl.type == ".ENDL":
                pnl.type = ".LIB"
            pnl.add_known_object(parsed_object.value, BoostParserInterface.boost_xdm_map_dict[parsed_object.types[0]])

        else:
            lst = []
            for typ in parsed_object.types:
                lst.append(BoostParserInterface.boost_xdm_map_dict[typ])
            pnl.add_lazy_statement(parsed_object.value, lst)
