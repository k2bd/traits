# (C) Copyright 2005-2024 Enthought, Inc., Austin, TX
# All rights reserved.
#
# This software is provided without warranty under the terms of the BSD
# license included in LICENSE.txt and may be redistributed only under
# the conditions described in the aforementioned license. The license
# is also available online at http://www.enthought.com/licenses/BSD.txt
#
# Thanks for using Enthought open source!

# configure_traits.py -- Sample code to demonstrate configure_traits()

# --[Imports]------------------------------------------------------------------
from traits.api import HasTraits, Str, Int


# --[Code]---------------------------------------------------------------------
class SimpleEmployee(HasTraits):
    first_name = Str
    last_name = Str
    department = Str

    employee_number = Str
    salary = Int


sam = SimpleEmployee()
sam.configure_traits()
