//-------------------------------------------------------------------------
//   Copyright 2002-2020 National Technology & Engineering Solutions of
//   Sandia, LLC (NTESS).  Under the terms of Contract DE-NA0003525 with
//   NTESS, the U.S. Government retains certain rights in this software.
//
//   This file is part of the Xyce(TM) XDM Netlist Translator.
//   
//   Xyce(TM) XDM is free software: you can redistribute it and/or modify
//   it under the terms of the GNU General Public License as published by
//   the Free Software Foundation, either version 3 of the License, or
//   (at your option) any later version.
//  
//   Xyce(TM) XDM is distributed in the hope that it will be useful,
//   but WITHOUT ANY WARRANTY; without even the implied warranty of
//   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
//   GNU General Public License for more details.
//   
//   You should have received a copy of the GNU General Public License
//   along with the Xyce(TM) XDM Netlist Translator.
//   If not, see <http://www.gnu.org/licenses/>.
//-------------------------------------------------------------------------


#ifndef HSPICE_EXPR_PARSER_INTERFACE_HPP
#define HSPICE_EXPR_PARSER_INTERFACE_HPP


#include <boost/python.hpp>
#include "boost_expr_parser_common.h"
#include "expr_parser_interface.hpp"
#include "ast_common.hpp"
#include <boost/algorithm/string.hpp>
#include <string>
#include <vector>
#include <queue>
#include <map>
#include <unordered_map>
#include <boost/python/suite/indexing/map_indexing_suite.hpp>

using namespace boost::python;

class HSPICEExprBoostParser 
{
    public:
        boost::python::dict dict;
        boost::python::list list;
        boost::python::list list2;
        std::vector<std::string> param_list;
        std::unordered_map<std::string, double> variable_map;
        std::unordered_map<std::string, std::string> function_map;
        std::unordered_map<std::string, std::map<int, std::string>> function_variable_map;

        BoostParsedExpr parseExpr(std::string pythonExpr);
        void import_func_statements(class dict & py_dict);
        void import_func_args(class dict & py_dict);
        void import_param_statements(class list & py_list);
        BoostEvaluatedExpr eval_statements(class list & py_list, class list & py_list_2);
        void print_maps();

};


BOOST_PYTHON_MODULE(HSpiceExprSpirit)
{
    boost::python::class_<HSPICEExprBoostParser>("HSPICEExprBoostParser")
        .def("parseExpr", &HSPICEExprBoostParser::parseExpr)
        .def_readwrite("py_dict", &HSPICEExprBoostParser::dict)
        .def_readwrite("py_list", &HSPICEExprBoostParser::list)
        .def_readwrite("py_list2", &HSPICEExprBoostParser::list2)
        .def("import_func_statements", &HSPICEExprBoostParser::import_func_statements)
        .def("import_func_args", &HSPICEExprBoostParser::import_func_args)
        .def("import_param_statements", &HSPICEExprBoostParser::import_param_statements)
        .def("eval_statements", &HSPICEExprBoostParser::eval_statements)
        .def("print_maps", &HSPICEExprBoostParser::print_maps)
        ;
}

#endif
