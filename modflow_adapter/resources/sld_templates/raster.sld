<?xml version="1.0" encoding="ISO-8859-1"?>
<StyledLayerDescriptor version="1.0.0" xmlns="http://www.opengis.net/sld" xmlns:ogc="http://www.opengis.net/ogc"
  xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
  xsi:schemaLocation="http://www.opengis.net/sld http://schemas.opengis.net/sld/1.0.0/StyledLayerDescriptor.xsd">
  <NamedLayer>
    <Name>head_raster</Name>
    <UserStyle>
      <Name>head_raster</Name>
      <Title>Head Raster</Title>
      <FeatureTypeStyle>
        <Rule>
          <RasterSymbolizer>
            <Opacity>1.0</Opacity>
            <ColorMap>
              <ColorMapEntry color="${env('color0','#fffff1')}" quantity="${env('val_no_data', 0)}" label="nodata" opacity="0"/>
              <ColorMapEntry color="${env('color0','#FF0000')}" quantity="${env('val0', 0.00001)}" label="0"/>
              <ColorMapEntry color="${env('color1','#FF3000')}" quantity="${env('val1', 10)}" label="1" />
              <ColorMapEntry color="${env('color2','#FF7000')}" quantity="${env('val2', 20)}" label="2" />
              <ColorMapEntry color="${env('color3','#FFA200')}" quantity="${env('val3', 30)}" label="3" />
              <ColorMapEntry color="${env('color4','#FFD000')}" quantity="${env('val4', 40)}" label="4" />
              <ColorMapEntry color="${env('color5','#FFFF00')}" quantity="${env('val5', 50)}" label="5"/>
              <ColorMapEntry color="${env('color6','#A2D05C')}" quantity="${env('val6', 60)}" label="6"/>
              <ColorMapEntry color="${env('color7','#45A2B9')}" quantity="${env('val7', 70)}" label="7"/>
              <ColorMapEntry color="${env('color8','#0080FF')}" quantity="${env('val8', 80)}" label="8" />
              <ColorMapEntry color="${env('color9','#003ea3')}" quantity="${env('val9', 90)}" label="9" />
            </ColorMap>
          </RasterSymbolizer>
        </Rule>
      </FeatureTypeStyle>
    </UserStyle>
  </NamedLayer>
</StyledLayerDescriptor>
