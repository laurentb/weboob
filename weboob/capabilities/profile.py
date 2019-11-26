# -*- coding: utf-8 -*-

# Copyright(C) 2016      Edouard Lambert
#
# This file is part of weboob.
#
# weboob is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# weboob is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with weboob. If not, see <http://www.gnu.org/licenses/>.


from .base import Capability, BaseObject, DecimalField, StringField, UserError
from .date import DateField

__all__ = ['Profile', 'Person', 'Company', 'CapProfile']


class ProfileMissing(UserError):
    """
    Raised when profile is not accessible
    """


class Profile(BaseObject):
    """
    Profile.
    """
    name =                        StringField('Full name or company name')
    address =                     StringField('Full Address')
    country =                     StringField('Country of owner')
    phone =                       StringField('Phone number')
    professional_phone =          StringField('Professional phone number')
    email =                       StringField('Mail of owner')
    professional_email =          StringField('Professional email of owner')
    main_bank =                   StringField('Main bank of owner')


class Person(Profile):
    """
    Person.
    """
    birth_date =                  DateField('Birth date')
    firstname =                   StringField("Person's firstname")
    lastname =                    StringField("Person's lastname")
    nationality =                 StringField('Nationality of owner')
    mobile =                      StringField('Mobile number of owner')
    gender =                      StringField('Gender of owner (Male/Female)')
    maiden_name =                 StringField('Maiden name')
    spouse_name =                 StringField('Name of spouse')
    children =                    DecimalField('Number of dependent children')
    family_situation =            StringField('Family situation')
    matrimonial =                 StringField('Matrimonial status')
    housing_status =              StringField('Housing status')
    job =                         StringField('Profession')
    job_start_date =              DateField('Start date of current job')
    job_activity_area =           StringField('Activity area of company')
    job_contract_type =           StringField('Contract type of current job')
    company_name =                StringField('Name of company')
    company_siren =               StringField('SIREN Number of company')
    socioprofessional_category =  StringField('Socio-Professional Category')


class Company(Profile):
    """
    Company.
    """
    siren =                       StringField('SIREN Number')
    registration_date  =          DateField('Registration date')
    activity_area =               StringField('Activity area')


class CapProfile(Capability):
    def get_profile(self):
        """
        Get profile.

        :rtype: :class:`Person` or :class:`Company`
        """
        raise NotImplementedError()
