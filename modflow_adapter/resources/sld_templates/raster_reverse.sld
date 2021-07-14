<?xml version="1.0" encoding="ISO-8859-1"?>
<StyledLayerDescriptor version="1.0.0" xmlns="http://www.opengis.net/sld" xmlns:ogc="http://www.opengis.net/ogc"
  xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
  xsi:schemaLocation="http://www.opengis.net/sld http://schemas.opengis.net/sld/1.0.0/StyledLayerDescriptor.xsd">
  <NamedLayer>
    <Name>low_blue_raser</Name>
    <UserStyle>
      <Name>low_bluet_raster</Name>
      <Title>Low Blue Raster</Title>
      <FeatureTypeStyle>
        <Rule>
          <RasterSymbolizer>
            <Opacity>1.0</Opacity>
            <ColorMap>
              <ColorMapEntry color="${env('color0','#fffff1')}" quantity="${env('val_no_data', 0)}" label="nodata" opacity="0"/>
              <ColorMapEntry color="${env('color0','#003ea3')}" quantity="${env('val0', 0.00001)}" label="0"/>
              <ColorMapEntry color="${env('color1','#0080FF')}" quantity="${env('val1', 10)}" label="1" />
              <ColorMapEntry color="${env('color2','#45A2B9')}" quantity="${env('val2', 20)}" label="2" />
              <ColorMapEntry color="${env('color3','#A2D05C')}" quantity="${env('val3', 30)}" label="3" />
              <ColorMapEntry color="${env('color4','#FFFF00')}" quantity="${env('val4', 40)}" label="4" />
              <ColorMapEntry color="${env('color5','#FFD000')}" quantity="${env('val5', 50)}" label="5"/>
              <ColorMapEntry color="${env('color6','#FFA200')}" quantity="${env('val6', 60)}" label="6"/>
              <ColorMapEntry color="${env('color7','#FF7000')}" quantity="${env('val7', 70)}" label="7"/>
              <ColorMapEntry color="${env('color8','#FF7000')}" quantity="${env('val8', 80)}" label="8" />
              <ColorMapEntry color="${env('color9','#FF0000')}" quantity="${env('val9', 90)}" label="9" />
            </ColorMap>
          </RasterSymbolizer>
        </Rule>
      </FeatureTypeStyle>
    </UserStyle>
  </NamedLayer>
</StyledLayerDescriptor>
