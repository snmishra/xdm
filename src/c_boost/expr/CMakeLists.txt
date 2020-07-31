#
# CMakeLists.txt for expression parser
#

set( XDM_EXPR_PARSER_SRC
    expr_parser_interface.cpp
    )
add_library( SpiritExprCommon SHARED ${XDM_EXPR_PARSER_SRC} )
target_link_libraries ( SpiritExprCommon ${PYTHON_LIBRARY} ${Boost_LIBRARIES} )
set_python_lib( SpiritExprCommon )

set( HSPICE_EXPR_PARSER_SRC
    hspice_expr_parser_interface.cpp
    )
add_library( HSpiceExprSpirit SHARED ${HSPICE_EXPR_PARSER_SRC} ${XDM_EXPR_PARSER_SRC} )
target_link_libraries ( HSpiceExprSpirit ${PYTHON_LIBRARY} ${Boost_LIBRARIES} SpiritExprCommon )
set_python_lib( HSpiceExprSpirit )

install_python_library( SpiritExprCommon )
install_python_library( HSpiceExprSpirit )
