"""
Python port of heterogeneity_coloring_function() from
PhysiCell-development/sample_projects/heterogeneity/custom_modules/custom.cpp:

    std::vector<std::string> heterogeneity_coloring_function( Cell* pCell )
    {
        double p = get_single_signal( pCell, "custom:oncoprotein");
        static double p_min = parameters.doubles( "oncoprotein_min" );
        static double p_max = parameters.doubles( "oncoprotein_max" );
        std::vector< std::string > output( 4, "black" );
        if( pCell->type == 1 )
        { return output; }
        if( pCell->phenotype.death.dead == false )
        {
            int oncoprotein = (int) round( (1.0/(p_max-p_min)) * (p-p_min) * 255.0 );
            char szTempString [128];
            sprintf( szTempString , "rgb(%u,%u,%u)", oncoprotein, oncoprotein, 255-oncoprotein );
            output[0].assign( szTempString );
            output[1].assign( szTempString );
            sprintf( szTempString , "rgb(%u,%u,%u)", (int)round(output[0][0]/p_max) , (int)round(output[0][1]/p_max) , (int)round(output[0][2]/p_max) );
            output[2].assign( szTempString );
            return output;
        }
        if( get_single_signal( pCell, "apoptotic") > 0.5 )
        {
            output[0] = "rgb(255,0,0)";
            output[2] = "rgb(125,0,0)";
        }
        if( get_single_signal(pCell, "necrotic") > 0.5 )
        {
            output[0] = "rgb(250,138,38)";
            output[2] = "rgb(139,69,19)";
        }
        return output;
    }

NOTE on a real bug in the C++ original, reproduced here for exact parity:
output[0][0]/[1]/[2] in the second sprintf() index the *characters* of the
string "rgb(...)" just assigned to output[0] -- i.e. 'r' (114), 'g' (103),
'b' (98), the literal prefix -- not numeric RGB channel values. So output[2]
(meant to be a dimmer/nucleus shade of the live-cell color) is actually a
constant, oncoprotein-independent color: rgb(round(114/p_max), round(103/p_max),
round(98/p_max)) -- for this config's oncoprotein_max=2, always rgb(57,52,49).
Reproduced as-is below for exact output parity with the real C++ build. If you
want the (probably intended) fix -- shading output[2] from the actual
oncoprotein-derived RGB values instead -- say so and I'll change it.
"""
import physicellpy as pc


def heterogeneity_coloring_function(cell):
    p = pc.get_single_signal(cell, "custom:oncoprotein")
    p_min = pc.parameters.doubles("oncoprotein_min")
    p_max = pc.parameters.doubles("oncoprotein_max")

    # immune cells are black
    output = ["black", "black", "black", "black"]
    if cell.type == 1:
        return output

    # live cells are green, but shaded by oncoprotein value
    if not cell.phenotype.death.dead:
        oncoprotein = round((1.0 / (p_max - p_min)) * (p - p_min) * 255.0)
        rgb = f"rgb({oncoprotein},{oncoprotein},{255 - oncoprotein})"
        output[0] = rgb
        output[1] = rgb
        # Reproduces the C++ string-indexing bug exactly -- see module
        # docstring. rgb[0], rgb[1], rgb[2] are always 'r', 'g', 'b'.
        ch0, ch1, ch2 = ord(rgb[0]), ord(rgb[1]), ord(rgb[2])
        output[2] = f"rgb({round(ch0 / p_max)},{round(ch1 / p_max)},{round(ch2 / p_max)})"
        return output

    # if not, dead colors
    if pc.get_single_signal(cell, "apoptotic") > 0.5:
        output[0] = "rgb(255,0,0)"
        output[2] = "rgb(125,0,0)"

    # Necrotic - Brown
    if pc.get_single_signal(cell, "necrotic") > 0.5:
        output[0] = "rgb(250,138,38)"
        output[2] = "rgb(139,69,19)"

    return output
