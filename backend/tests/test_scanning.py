"""Tests for the scanning engine: patterns, determinism, duration effects."""

import numpy as np
import pytest

from lidar_analysis . simulation . scanning import(
	MechanicalSpinningScanner ,
	StructuredRasterScanner ,
	NonRepetitiveScanner ,
	build_scan_pattern ,
)


def u( d ) :
	return np . sqrt(( d * d ) . sum( axis =int( 1 ) ) )


def spin_cfg( dur ) :
	return{
		"channel_count" : int( 16 ) ,
		"channel_angles_rad" : np . deg2rad( np . arange( int( 16 ) , dtype = np . float64 ) * float( 1 ) - float( 7.5 ) ) ,
		"horizontal_fov_rad" :( float( 0 ) , float( 2 ) * np . pi ) ,
		"horizontal_resolution_deg" : float( 0.1 ) ,
		"rotation_frequency_hz" : float( 1 ) ,
		"duration_seconds" : float( dur ) ,
	}


def test_spinning_duration_scales_ray_count( ) :
	a = MechanicalSpinningScanner( spin_cfg( float( 1 ) ) )
	rng = np . random . default_rng( int( 123 ) )
	d1 , _ =a . generate_rays( float( 0 ) , float( 1 ) , rng )
	b = MechanicalSpinningScanner( spin_cfg( float( 0.5 ) ) )
	rng = np . random . default_rng( int( 123 ) )
	d2 , _ =b . generate_rays( float( 0 ) , float( 0.5 ) , rng )
	per_rot = a . channel_count * int( a . _azimuth_bins( )[ int( 1 ) ] )
	assert abs( float( len( d1 ) ) / float( per_rot ) - float( 1 ) ) < float( 0.02 )
	assert abs( float( len( d2 ) ) / float( 0.5 ) / float( len( d1 ) ) - float( 1 ) ) < float( 0.02 )
	assert len( d2 ) < len( d1 )


def test_spinning_azimuth_within_fov_and_unit( ) :
	a = MechanicalSpinningScanner( spin_cfg( float( 1 ) ) )
	d , m =a . generate_rays( float( 0 ) , float( 1 ) , np . random . default_rng( int( 1 ) ) )
	assert float( m[ "azimuth" ] . min( ) ) >= float( -0.01 )
	assert float( m[ "azimuth" ] . max( ) ) <= float( 2 ) * np . pi + float( 0.01 )
	nrm =u( d )
	assert float( nrm . min( ) ) > float( 0.999 )
	assert float( nrm . max( ) ) < float( 1.001 )
	assert len( m[ "azimuth" ] ) == len( d )
	assert len( m[ "channel" ] ) == len( d )


def test_spinning_determinism( ) :
	a = MechanicalSpinningScanner( spin_cfg( float( 1 ) ) )
	r1 = np . random . default_rng( int( 7 ) )
	d1 , _ =a . generate_rays( float( 0 ) , float( 1 ) , r1 )
	r2 = np . random . default_rng( int( 7 ) )
	d2 , _ =a . generate_rays( float( 0 ) , float( 1 ) , r2 )
	assert np . array_equal( d1 , d2 )


def test_raster_grid_and_ordering( ) :
	cfg ={
		"horizontal_fov_deg" : float( 10 ) ,
		"vertical_fov_deg" : float( 8 ) ,
		"horizontal_step_deg" : float( 1 ) ,
		"vertical_step_deg" : float( 1 ) ,
		"frame_rate_hz" : float( 2 ) ,
		"duration_seconds" : float( 1 ) ,
	}
	cfg[ "horizontal_fov_rad" ] = np . deg2rad( float( 10 ) )
	cfg[ "vertical_fov_rad" ] = np . deg2rad( float( 8 ) )
	cfg[ "horizontal_step_rad" ] = np . deg2rad( float( 1 ) )
	cfg[ "vertical_step_rad" ] = np . deg2rad( float( 1 ) )
	cfg[ "scan_ordering" ] = "row_major"
	r = StructuredRasterScanner( cfg )
	nrow , ncol = r . grid_dims( )
	assert nrow == int( 9 )
	assert ncol == int( 11 )
	perfr = int( nrow * ncol )
	d , m =r . generate_rays( float( 0 ) , float( 1 ) , np . random . default_rng( int( 1 ) ) )
	nf = int( m[ "frame" ] . max( ) ) + int( 1 )
	assert nf == int( 2 )
	assert len( d ) == nf * perfr
	az = m[ "azimuth" ][ : ncol ]
	assert bool( np . all( np . diff( az ) > float( 0 ) ) )
	assert float( m[ "t" ] . max( ) ) <= float( 1.0001 )


def test_nonrepetitive_coverage_and_rays( ) :
	n = NonRepetitiveScanner({
		"fov_az_rad" : float( 30 ) ,
		"fov_el_rad" : float( 10 ) ,
		"nominal_point_rate_hz" : float( 50 ) ,
		"coverage_model" : "lissajous" ,
	})
	tiny = n . expected_coverage( float( 0.01 ) )
	m1 = n . expected_coverage( float( 1 ) )
	m10 = n . expected_coverage( float( 10 ) )
	assert tiny > float( 0 )
	assert tiny < float( 0.01 )
	assert m1 > tiny
	assert m10 > m1
	assert m10 <= float( 1 )
	rng1 = np . random . default_rng( int( 3 ) )
	d1 , _ =n . generate_rays( float( 0 ) , float( 1 ) , rng1 )
	rng2 = np . random . default_rng( int( 3 ) )
	d2 , _ =n . generate_rays( float( 0 ) , float( 1 ) , rng2 )
	assert np . array_equal( d1 , d2 )
	assert float( len( d1 ) ) == float( 50 )
	assert float( u( d1 ) . max( ) ) <= float( 1.001 )
	with pytest . raises( ValueError ) :
		NonRepetitiveScanner({
			"coverage_model" : "bogus" ,
		})


def test_factory_builds_three_types( ) :
	scan ={
		"type" : "mechanical_spinning" ,
		"channel_count" :{ "value" :int( 8 ) , "unit" :None } ,
		"horizontal_resolution" :{ "value" :float( 1 ) , "unit" :"deg" } ,
		"rotation_frequency" :{ "value" :float( 2 ) , "unit" :"Hz" } ,
		"duration" :{ "value" :float( 0.5 ) , "unit" :"s" } ,
	}
	raster ={
		"type" : "structured_raster" ,
		"horizontal_resolution" :{ "value" :float( 1 ) , "unit" :"deg" } ,
		"vertical_resolution" :{ "value" :float( 1 ) , "unit" :"deg" } ,
		"frame_rate" :{ "value" :float( 2 ) , "unit" :"Hz" } ,
		"scan_ordering" :"column_major" ,
		"duration" :{ "value" :float( 1 ) , "unit" :"s" } ,
	}
	nrd ={
		"type" : "non_repetitive" ,
		"horizontal_fov" :{ "value" :float( 30 ) , "unit" :"deg" } ,
		"vertical_fov" :{ "value" :float( 10 ) , "unit" :"deg" } ,
		"nominal_point_rate" :{ "value" :float( 50 ) , "unit" :"Hz" } ,
		"duration" :{ "value" :float( 1 ) , "unit" :"s" } ,
	}
	s = build_scan_pattern( scan )
	r = build_scan_pattern( raster )
	n = build_scan_pattern( nrd )
	assert isinstance( s , MechanicalSpinningScanner )
	assert isinstance( r , StructuredRasterScanner )
	assert isinstance( n , NonRepetitiveScanner )
	assert s . params[ "type" ] == "mechanical_spinning"
	assert r . params[ "type" ] == "structured_raster"
	assert n . params[ "type" ] == "non_repetitive"
	d , _ =s . generate_rays( float( 0 ) , float( 0.5 ) , np . random . default_rng( int( 1 ) ) )
	assert float( len( d ) ) > float( 0 )