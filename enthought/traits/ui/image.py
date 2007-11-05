#------------------------------------------------------------------------------
#
#  Copyright (c) 2005, Enthought, Inc.
#  All rights reserved.
# 
#  This software is provided without warranty under the terms of the BSD
#  license included in enthought/LICENSE.txt and may be redistributed only
#  under the conditions described in the aforementioned license.  The license
#  is also available online at http://www.enthought.com/licenses/BSD.txt
#  Thanks for using Enthought open source!
# 
#  Author: David C. Morrill
#  Date:   11/03/2007
#
#------------------------------------------------------------------------------

""" Defines the Image object used to manage Traits UI image libraries.
"""

#-------------------------------------------------------------------------------
#  Imports:
#-------------------------------------------------------------------------------

from os \
    import environ, listdir, remove
    
from os.path \
    import join, isdir, isfile, join, splitext, abspath, basename, exists
    
from platform \
    import system
    
from zipfile \
    import is_zipfile, ZipFile, ZIP_DEFLATED
    
from enthought.traits.api \
    import HasPrivateTraits, HasStrictTraits, Property, Str, Int, List, Dict, \
           File, Instance, Bool, cached_property
           
from enthought.traits.trait_base \
    import get_resource_path
    
from enthought.traits.ui.theme \
    import Theme

from enthought.pyface.api \
    import ImageResource
    
from enthought.pyface.resource_manager \
    import resource_manager
    
from enthought.resource.resource_reference \
    import ImageReference
    
#-------------------------------------------------------------------------------
#  'ImageLibrary' class:
#-------------------------------------------------------------------------------

class ImageLibrary ( HasPrivateTraits ):
    """ Manages Traits UI image libraries.
    """
    
    # The list of available image volumes:
    volumes = Property
    
    # The volume dictionary (the keys are volume names, and the values are the
    # corresponding ImageVolume objects):
    catalog = Property
    
    #-- Private Traits ---------------------------------------------------------
    
    # Mapping from a 'virtual' library name to a 'real' library name:
    aliases = Dict

    #-- Public methods ---------------------------------------------------------
    
    def image_resource ( self, image_name ):
        """ Returns an ImageResource object for the specified image name.
        """
        # If no volume was specified, use the standard volume:
        if image_name.find( ':' ) < 0:
            image_name = '@images:%s' % image_name[1:]
            
        # Find the correct volume, possible resolving any aliases used:
        volume = self._find_volume( image_name )
        
        # Find the image within the volume and return its ImageResource object:
        if volume is not None:
            return volume.image_resource( image_name )
        
        # Otherwise, the volume was not found:
        return None
    
    def add_volume ( self, file_name = None ):
        """ If **file_name** is a file, it adds an image volume specified by
            **file_name** to the image library. If **file_name** is a 
            directory, it adds all image libraries contained in the directory 
            to the image library. If **file_name** is omitted, all image 
            libraries located in the *images* directory contained in the same 
            directory as the caller are added.
        """
        # If no file name was specfied, derive a path from the caller's
        # source code location:
        if file_name is None:
            file_name = join( get_resource_path( 2 ), 'images' )
            
        if isfile( file_name ):
            # Load an image volume from the specified file:
            volume = self._add_volume( file_name )
            if volume is None:
                raise TraitError( "'%s' is not a valid image volume." % 
                                  file_name )
            if volume.name in self.catalog:
                self._duplicate_volume( volume.name )
            self.catalog[ volume.name ] = volume
            self.volumes.append( volume )
            
        elif isdir( file_name ):
            # Load all image volumes from the specified path:
            catalog = self.catalog
            volumes = self._add_path( file_name )
            for volume in volumes:
                if volume.name in catalog:
                    self._duplicate_volume( volume.name )
                catalog[ volume.name ] = volume
                
            self.volumes.extend( volumes )
        else:
            # Handle an unrecognized argument:
            raise TraitError( "The add method argument must be None or a file "
                      "or directory path, but '%s' was specified." % file_name )
                      
    def add_path ( self, volume_name, path = None ):
        """ Adds the directory specified by **path** as a *virtual* volume
            called **vlume_name**. All image files contained within path define
            the contents of the volume. If **path** is None, the *images*
            contained in the same directory as the caller are is used as the
            path for the *virtual* volume..
        """
        pass # fixme: Implement this...
        
    def extract ( self, file_name, image_names ):
        """ Builds a new image volume called **file_name** from the list of
            image names specified by **image_names**. Each image name should be
            of the form: '@volume:name'.
        """
        # Get the volume name and file extension:
        volume_name, ext = splitext( basename( file_name ) )
        
        # If no extension specified, add the '.zip' file extension:
        if ext == '':
            file_name += '.zip'
            
        # Create the ImageVolume object to describe the new volume:
        volume = ImageVolume( name = volume_name )
            
        # Make sure the zip file does not already exists:
        if exists( file_name ):
            raise TraitError( "The '%s' file already exists." % file_name )
        
        # Create the zip file:
        zf = ZipFile( file_name, 'w', ZIP_DEFLATED )
        
        # Add each of the specified images to it and the ImageVolume:
        try:
            error    = True
            licenses = set()
            for image_name in image_names:
                col = image_name.find( ':' )
                
                # Verify the image name is legal:
                if (image_name[:1] != '@') or (col < 0):
                    raise TraitError( ("The image name specified by '%s' is "
                                "not of the form: @volume:name.") % image_name )
                                       
                # Get the volume for the image name:
                volume = self._find_volume( image_name )
                if volume is None:
                    raise TraitError( ("Could not find the image volume "
                                       "specified by '%s'.") % image_name )
                                       
                # Get the image info:
                info = volume.catalog.get( image_name )
                if info is None:
                    raise TraitError( ("Could not find the image specified by "
                                       "'%s'.") % image_name )
                                     
                # Add the image info to the volume:
                volume.images.append( info )
                
                # Add the image file to the zip file:
                name = image_name[ col + 1: ]
                zf.writestr( name, volume.image_data( image_name ) )
                
                # Update the license information for the new zip file:
                licenses.add( volume.license )
                                             
            # Create the final license information for the volume:
            volume.licenses = list( licenses )
            
            # Write the volume manifest to the zip file:
            zp.writestr( 'manifest.py', volume.image_volume )
            
            # Write a separate licenses file for human consumption:
            zp.writestr( 'license.txt', 
                         ('\n%s\n' % ('-' * 79)).join( volume.licenses ) )
            
            # Indicate no errors occurred:
            error = False
        finally:
            zf.close()
            if error:
                remove( file_name )
        
    #-- Property Implementations -----------------------------------------------
    
    @cached_property
    def _get_volumes ( self ):
        result = self._add_path( join( get_resource_path( 1 ), 'library' ) )
        paths  = environ.get( 'TRAITS_IMAGES' )
        if paths is not None:
            separator = ';'
            if system() != 'Windows':
                separator = ':'
                
            for path in paths.split( separator ):
                result.extend( self._add_path( path ) )
                
        return result

    @cached_property
    def _get_catalog ( self ):
        return dict( [ ( volume.name, volume ) for volume in self.volumes ] )
        
    #-- Private Methods --------------------------------------------------------
    
    def _add_path ( self, path ):
        """ Returns a list of ImageVolume objects, one for each image library
            located in the specified **path**.
        """
        result = []
        if isdir( path ):
            for base in listdir( path ):
                if splitext( base )[1] == '.zip':
                    volume = self._add_volume( join( path, base ) )
                    if volume is not None:
                        result.append( volume )
                        
        return result
            
    def _add_volume ( self, path ):
        """ Returns an ImageVolume object for the image library specified by
            **path**. If **path** does not specify a valid ImageVolume, None is
            returned.
        """
        if is_zipfile( path ):
            zf = ZipFile( path, 'r' )
            try:
                if 'manifest.py' in zf.nameslist():
                    temp = {}
                    exec zf.read( 'manifest.py' ) in globals(), temp
                    volume = temp.get( 'volume' )
                    if isinstance( volume, ImageVolume ):
                        aka  = set()
                        name = volume.name
                        for image in volume.images:
                            image_name = image.image_name
                            vname      = image_name[ 1: image_name.find( ':' ) ]
                            if vname != name:
                                aka.add( vname )
                            
                        aliases = self.aliases
                        for vname in aka:
                            if ((vname in aliases) and
                                (name != aliases[ vname ])):
                                raise TraitError( ("Image library error: "
                                    "Attempt to alias '%s' to '%s' when it is "
                                    "already aliased to '%s'") %
                                    ( vname, name, aliases[ name ] ) )
                            aliases[ vname ] = name
                        
                        volume.path = abspath( path )
                        
                        return volume
            finally:
                zf.close()
            
        return None
        
    def _find_volume ( self, image_name ):
        """ Returns the ImageVolume object corresponding to the specified
            **image_name** or None if the volume cannot be found.
        """
        # Extract the volume name from the image name:
        volume_name = image_name[ 1: image_name.find( ':' ) ]
        
        # Find the correct volume, possibly resolving any aliases used:
        catalog = self.catalog
        aliases = self.aliases
        while volume_name not in catalog:
            volume_name = aliases.get( volume_name )
            if volume_name is None:
                return None
                
        return catalog[ volume_name ] 

    def _duplicate_volume ( self, volume_name ):
        """ Raises a duplicate volume name error.
        """
        raise TraitError( ("Attempted to add an image volume called '%s' when "
                  "a volume with that name is already defined.") % volume_name )
        
# Create the singleton image object:        
ImageLibrary = ImageLibrary()        
        
#-------------------------------------------------------------------------------
#  'ImageInfo' class:
#-------------------------------------------------------------------------------

class ImageInfo ( HasStrictTraits ):
    """ Defines a class that contains information about a specific Traits UI 
        image.
    """
    
    # The user friendly name of the image:
    name = Str
    
    # The full image name (e.g. '@standard:floppy'):
    image_name = Str
    
    # A description of the image:
    description = Str
    
    # The category that the image belongs to:
    category = Str( 'General' )
    
    # A list of keywords used to describe/categorize the image:
    keywords = List( Str )
    
    # The image width (in pixels):
    width = Int
    
    # The image height (in pixels):
    height = Int
    
    # The theme for this image:
    theme = Instance( Theme )
    
    # A read-only string containing the Python code needed to construct this
    # ImageInfo object:
    image_info_code = Property
    
    # A read-only string containing the Python code needed to construct the 
    # Theme object for the image:
    theme_code = Property
    
    #-- Default Value Implementations ------------------------------------------
    
    def _theme_default ( self ):
        return Theme( self.image_name )
    
    #-- Property Implementations -----------------------------------------------
        
    @cached_property
    def _get_image_info ( self ):
        data = dict( [ ( name, repr( value ) ) 
                       for name, value in self.get( 'name', 'image_name', 
                         'description', 'category', 'keywords' ).iteritems() ] )
        data.update( self.get( 'width', 'height', 'theme_code' ) )
        return (ImageInfoTemplate % data)
    
    @cached_property
    def _get_theme_code ( self ):
        data = self.theme.get()
        data[ 'image_name' ] = self.image_name
        data.update( self.theme.margins.get() )
        return (ThemeTemplate % data)
        
#-------------------------------------------------------------------------------
#  'ImageVolume' class:
#-------------------------------------------------------------------------------

class ImageVolume ( HasPrivateTraits ):

    # The canonical name of this volume:
    name = Str
    
    # A description of this volume:
    description = Str
    
    # The category that the volume belongs to:
    category = Str
    
    # A list of keywords used to describe the volume:
    keywords = List( Str )

    # The list of licenses that apply to the volume and its contents:
    licenses = List( Str )
    
    # The path of the file that defined this volume:
    path = File
    
    # Is the path a zip file?
    is_zip_file = Bool( True )
    
    # The list of images available in the volume:
    images = List( ImageInfo )
    
    # A dictionary mapping image names to ImageInfo objects:
    catalog = Property
    
    # A read-only string containing the Python code needed to construct this
    # ImageVolume object:
    image_volume = Property
    
    #-- Public Methods ---------------------------------------------------------
    
    def image_resource ( self, image_name ):
        """ Returns the ImageResource object for the specified **image_name**,
            or None if **image_name** cannot be found.
        """
        info = self.catalog.get( image_name )
        if info is not None:
            name = image_name[ image_name.find( ':' ) + 1: ]
            if splitext( name )[1] == '':
                name += '.png'
                
            if self.is_zip_file:
                zf  = ZipFile( self.path, 'r' )
                ref = ImageReference( resource_manager.resource_factory,
                                      data = zf.read( name ) )
                zf.close()
            else:
                ref = ImageReference( resource_manager.resource_factory,
                                      filename = join( self.path, name ) )
                                      
            return ImageResource( _ref = ref )
            
        return None
    
    #-- Property Implementations -----------------------------------------------
    
    @cached_property
    def _get_catalog ( self ):
        return dict( [ ( image.image_name, image ) for image in self.images ] )
        
    @cached_property
    def _get_image_volume ( self ):
        data = dict( [ ( name, repr( value ) ) 
                       for name, value in self.get( 'name', 'description',
                                 'category', 'keywords', 'licenses'
                             ).iteritems() ] )
        data['images'] = '[\n%s\n    ]' % (',\n'.join( [ info.image_info_code 
                                                    for info in self.images ] ))
        return (ImageVolumeTemplate % data)

#-- Code Generation Templates --------------------------------------------------

# Template for creating an ImageVolume object:
ImageVolumeTemplate = """manifest = ImageVolume(
    name        = %(name)s,
    description = %(description)s,
    category    = %(category)s,
    keywords    = %(keywords)s,
    licenses    = %(licenses)s,
    paths       = %(paths)s,
    images      = %(images)s
)"""    

# Template for creating an ImageInfo object:
ImageInfoTemplate = """
        ImageInfo(
            name        = %(name)s,
            image_name  = %(image_name)s,
            description = %(description)s,
            category    = %(category)s,
            keywords    = %(keywords)s,
            width       = %(width)d,
            height      = %(height)d,
            theme       = %(theme_code)s
        )"""
    
# Template for creating a Theme object:    
ThemeTemplate = """Theme( %(image_name)s,
                margins   = Margins( %(left)d, %(right)%d, %(top)d, %(bottom)d ),
                offset    = %(offset)s,
                alignment = "%(alignment)s"
            )"""
            