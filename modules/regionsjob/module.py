# -*- coding: utf-8 -*-

# Copyright(C) 2014      Bezleputh
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.

from collections import OrderedDict

from weboob.tools.backend import Module, BackendConfig
from weboob.capabilities.job import CapJob, BaseJobAdvert
from .browser import RegionsjobBrowser
from weboob.tools.value import Value


__all__ = ['RegionsjobModule']


class RegionsjobModule(Module, CapJob):
    NAME = 'regionsjob'
    DESCRIPTION = u'regionsjob website'
    MAINTAINER = u'Bezleputh'
    EMAIL = 'carton_ben@yahoo.fr'
    LICENSE = 'AGPLv3+'
    VERSION = '1.5'

    BROWSER = RegionsjobBrowser

    website_choices = OrderedDict([(k, u'%s (%s)' % (v, k)) for k, v in sorted({
        'www.centrejob.com': u'CentreJob',
        'www.estjob.com': u'EstJob',
        'www.nordjob.com': u'NordJob',
        'www.ouestjob.com': u'OuestJob',
        'www.pacajob.com': u'PacaJob',
        'www.parisjob.com': u'ParisJob',
        'www.rhonealpesjob.com': u'RhoneAlpesJob',
        'www.sudouestjob.com': u'SudOuestJob',
        'www.jobtrotter.com': u'JobTrotter',
    }.items())])

    fonction_choices = OrderedDict([(k, u'%s' % (v)) for k, v in sorted({
        '': u'Indifferent',
        'Assistanat_admin_accueil': u'Assistanat/Adm.ventes/Accueil',
        'BTP_gros_second_oeuvre': u'BTP - Gros Oeuvre/Second Oeuvre',
        'Bureau_etude_R_D': u'Bureau d\'Etudes/R & D/BTP archi/conception',
        'Commercial_technico_com': u'Commercial - Technico-Commercial',
        'Commercial_particulier': u'Commercial auprès des particuliers',
        'Commercial_professionnel': u'Commercial auprès des professionnels',
        'Commercial_vendeur': u'Commercial-Vendeur en magasin',
        'Compta_gestion_finance_audit': u'Compta/Gestion/Finance/Audit',
        'Dir_resp_centre_profit': u'Direction/Resp. Co. et Centre de Profit',
        'Import_export_inter': u'Import/Export/International',
        'Informatique_dev_hard': u'Informatique - Dével. Hardware',
        'Informatique_dev': u'Informatique - Développement',
        'Informatique_syst_info': u'Informatique - Systèmes d\'Information',
        'Informatique_syst_reseaux': u'Informatique - Systèmes/Réseaux',
        'Ingenierie_agro_agri': u'Ingénierie - Agro/Agri',
        'Ingenierie_chimie_pharma_bio': u'Ingénierie - Chimie/Pharmacie/Bio.',
        'Ingenierie_electro_tech': u'Ingénierie - Electro-tech./Automat.',
        'Ingenierie_meca_aero': u'Ingénierie - Mécanique/Aéron.',
        'Ingenierie_telecom': u'Ingénierie - Telecoms/Electronique',
        'Juridique_droit': u'Juridique/Droit',
        'Logistique_metiers_transport': u'Logistique/Métiers du Transport',
        'Marketing_com_graphisme': u'Marketing/Communication/Graphisme',
        'Dir_management_resp': u'Métiers de la distribution - Management/Resp.',
        'Metiers_fonction_publique': u'Métiers de la Fonction Publique',
        'Negociation_gest_immo': u'Négociation/Gestion immobilière',
        'Production_gestion': u'Production - Gestion/Maintenance',
        'Production_operateur': u'Production - Opérateur/Manoeuvre',
        'Qualite_securite_environnement': u'Qualité/Hygiène/Sécurité/Environnement',
        'Restauration_hotellerie_tourisme': u'Restauration/Tourisme/Hôtellerie/Loisirs',
        'RH_Personnel_Formation': u'RH/Personnel/Formation',
        'Sante_social': u'Santé/Social',
        'SAV_Hotline': u'SAV/Hotline/Téléconseiller',
        'Services_pers_entreprises': u'Services à la personne/aux entreprises',
    }.items())])

    secteur_choices = OrderedDict([(k, u'%s' % (v)) for k, v in sorted({
        '': u'Indifferent',
        'Agri_peche': u'Agriculture/Pêche',
        'Banq_assur_finan': u'Banque/Assurance/Finance',
        'BTP': u'BTP',
        'Distrib_commerce': u'Distribution/Commerce de gros',
        'Enseign_forma': u'Enseignement/Formation',
        'Immo': u'Immobilier',
        'Ind_aero': u'Industrie Aéronautique/Aérospatial',
        'Ind_agro': u'Industrie Agro-alimentaire',
        'Ind_auto_meca_nav': u'Industrie Auto/Meca/Navale',
        'Ind_hightech_telecom': u'Industrie high-tech/Telecom',
        'Ind_manufact': u'Industrie Manufacturière',
        'Ind_petro': u'Industrie Pétrolière/Pétrochimie',
        'Ind_pharma_bio_chim': u'Industrie Pharmaceutique/Biotechn./Chimie',
        'Media_internet_com': u'Média/Internet/Communication',
        'Resto': u'Restauration',
        'Sante_social': u'Santé/Social/Association',
        'Energie_envir': u'Secteur Energie/Environnement',
        'Inform_SSII': u'Secteur informatique/SSII',
        'Serv_public_autre': u'Service public autres',
        'Serv_public_collec_terri': u'Service public des collectivités territoriales',
        'Serv_public_etat': u'Service public d\'état',
        'Serv_public_hosp': u'Service public hospitalier',
        'Serv_entreprise': u'Services aux Entreprises',
        'Serv_pers_part': u'Services aux Personnes/Particuliers',
        'Tourism_hotel_loisir': u'Tourisme/Hôtellerie/Loisirs',
        'Transport_logist': u'Transport/Logistique',
    }.items())])

    experience_choices = OrderedDict([(k, u'%s' % (v)) for k, v in sorted({
        '      ': u'Indifferent',
        'Inf_1': u'- 1 an',
        '1_7': u'1 à 7 ans',
        'Sup_7': u'+ 7 ans',
    }.items())])

    contract_choices = OrderedDict([(k, u'%s' % (v)) for k, v in sorted({
        '': u'Tous types de contrat',
        'CDD': u'CDD',
        'CDI': u'CDI',
        'Stage': u'Stage',
        'Travail_temp': u'Travail temporaire',
        'Alternance': u'Alternance',
        'Independant': u'Indépendant',
        'Franchise': u'Franchise',
    }.items())])

    qualification_choice = OrderedDict([(k, u'%s' % (v)) for k, v in sorted({
        '': u'Indifferent',
        'BEP_CAP': u'BEP/CAP',
        'Employe_Operateur': u'Employé/Opérateur/Ouvrier Spe/Bac',
        'Technicien_B2': u'Technicien/Employé Bac +2',
        'Agent_maitrise_B3': u'Agent de maîtrise/Bac +3/4',
        'Ingenieur_B5': u'Ingénieur/Cadre/Bac +5',
        'Cadre_dirigeant': u'> Bac + 5 (cadre dirigeant)',
    }.items())])

    enterprise_type_choice = OrderedDict([(k, u'%s' % (v)) for k, v in sorted({
        '': u'Tous types d\'entreprises',
        'Cabinet_recr': u'Cabinets de recrutement',
        'Entreprises': u'Entreprises',
        'SSII': u'SSII',
        'Travail_temporaire': u'Travail temporaire',
    }.items())])

    CONFIG = BackendConfig(Value('website', label=u'Region', choices=website_choices),
                           Value('place', label='Place', masked=False, default=''),
                           Value('metier', label='Job name', masked=False, default=''),
                           Value('fonction', label=u'Fonction', choices=fonction_choices, default=''),
                           Value('secteur', label=u'Secteur', choices=secteur_choices, default=''),
                           Value('contract', label=u'Contract', choices=contract_choices, default=''),
                           Value('experience', label=u'Experience', choices=experience_choices, default=''),
                           Value('qualification', label=u'Qualification', choices=qualification_choice, default=''),
                           Value('enterprise_type', label=u'Enterprise type',
                                 choices=enterprise_type_choice, default=''))

    def create_default_browser(self):
        return self.create_browser(self.config['website'].get())

    def search_job(self, pattern=''):
        return self.browser.search_job(pattern=pattern)

    def advanced_search_job(self):
        return self.browser.search_job(pattern=self.config['metier'].get(),
                                       fonction=self.config['fonction'].get(),
                                       secteur=self.config['secteur'].get(),
                                       contract=self.config['contract'].get(),
                                       experience=self.config['experience'].get().strip(),
                                       qualification=self.config['qualification'].get(),
                                       enterprise_type=self.config['enterprise_type'].get(),
                                       place=self.config['place'].get())

    def get_job_advert(self, _id, advert=None):
        return self.browser.get_job_advert(_id, advert)

    def fill_obj(self, advert, fields):
        return self.get_job_advert(advert.id, advert)

    OBJECTS = {BaseJobAdvert: fill_obj}
