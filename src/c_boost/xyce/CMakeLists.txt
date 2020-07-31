#
# CMakeLists.txt for xyce XDM parser stuff.
#

# Create the xdmparser target.
set( XDM_PARSER_SRC
    parser_interface.cpp
    )
add_library( SpiritCommon SHARED ${XDM_PARSER_SRC} )
target_link_libraries ( SpiritCommon ${PYTHON_LIBRARY} ${Boost_LIBRARIES} )
set_python_lib( SpiritCommon )


# Create the hspiceparser target.
set( HSPICE_PARSER_SRC
    hspice_parser_interface.cpp
    )
add_library( HSpiceSpirit SHARED ${HSPICE_PARSER_SRC} ${XDM_PARSER_SRC})
target_link_libraries ( HSpiceSpirit ${PYTHON_LIBRARY} ${Boost_LIBRARIES} SpiritCommon )
set_python_lib( HSpiceSpirit )


# Create the pspiceparser target.
set( PSPICE_PARSER_SRC
    pspice_parser_interface.cpp
    )
add_library( PSpiceSpirit SHARED ${PSPICE_PARSER_SRC} ${XDM_PARSER_SRC})
target_link_libraries ( PSpiceSpirit ${PYTHON_LIBRARY} ${Boost_LIBRARIES} SpiritCommon )
set_python_lib( PSpiceSpirit )


# Create the spectreparser target.
set( SPECTRE_PARSER_SRC
    spectre_parser_interface.cpp
    )
add_library( SpectreSpirit SHARED ${SPECTRE_PARSER_SRC} ${XDM_PARSER_SRC} )
target_link_libraries ( SpectreSpirit ${PYTHON_LIBRARY} ${Boost_LIBRARIES} SpiritCommon )
set_python_lib( SpectreSpirit )


# Create the tspiceparser target.
set( TSPICE_PARSER_SRC
    tspice_parser_interface.cpp
    )
add_library( TSpiceSpirit SHARED ${TSPICE_PARSER_SRC} ${XDM_PARSER_SRC} )
target_link_libraries (TSpiceSpirit ${PYTHON_LIBRARY} ${Boost_LIBRARIES} SpiritCommon )
set_python_lib( TSpiceSpirit )


# Create the xyceparser target.
set( XYCE_PARSER_SRC
    xyce_parser_interface.cpp
    )
add_library( XyceSpirit SHARED ${XYCE_PARSER_SRC} ${XDM_PARSER_SRC} )
target_link_libraries ( XyceSpirit ${PYTHON_LIBRARY} ${Boost_LIBRARIES} SpiritCommon )
set_python_lib( XyceSpirit )


install_python_library( SpiritCommon )
install_python_library( HSpiceSpirit )
install_python_library( PSpiceSpirit )
install_python_library( SpectreSpirit )
install_python_library( TSpiceSpirit )
install_python_library( XyceSpirit )

