# -*- coding: utf-8 -*-

# Copyright(C) 2013      Bezleputh
#
# This file is part of weboob.
#
# weboob is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# weboob is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with weboob. If not, see <http://www.gnu.org/licenses/>.


from weboob.tools.backend import BaseBackend, BackendConfig
from weboob.capabilities.job import ICapJob
from weboob.tools.ordereddict import OrderedDict
from weboob.tools.value import Value
from .browser import ApecBrowser
from .job import ApecJobAdvert

__all__ = ['ApecBackend']


class ApecBackend(BaseBackend, ICapJob):
    NAME = 'apec'
    DESCRIPTION = u'apec website'
    MAINTAINER = u'Bezleputh'
    EMAIL = 'carton_ben@yahoo.fr'
    VERSION = '0.h'

    BROWSER = ApecBrowser

    places_choices = OrderedDict([(k, u'%s' % (v)) for k, v in sorted({
        ' ': u'-- Indifférent --',
        '700': u'Alsace',
        '701': u'Aquitaine',
        '702': u'Auvergne',
        '703': u'Basse-Normandie',
        '704': u'Bourgogne',
        '705': u'Bretagne',
        '706': u'Centre',
        '707': u'Champagne',
        '20': u'Corse',
        '99712': u'France Outre-Mer',
        '709': u'Franche-Comté',
        '710': u'Haute-Normandie',
        '711': u'Ile-de-France',
        '712': u'Languedoc-Roussillon',
        '713': u'Limousin',
        '714': u'Lorraine',
        '715': u'Midi-Pyrénées',
        '716': u'Nord-Pas-de-Calais',
        '720': u'PACA',
        '717': u'Pays de La Loire',
        '718': u'Picardie',
        '719': u'Poitou-Charentes',
        '721': u'Rhône-Alpes',
        '99109': u'Allemagne',
        '99106': u'Estonie',
        '99108': u'Lituanie',
        '99116': u'République Tchèque',
        '99110': u'Autriche',
        '99105': u'Finlande',
        '99137': u'Luxembourg',
        '99114': u'Roumanie',
        '99131': u'Belgique',
        '99126': u'Grèce',
        '99144': u'Malte',
        '99132': u'Royaume Uni',
        '99111': u'Bulgarie',
        '99112': u'Hongrie',
        '99135': u'Pays Bas',
        '99117': u'Slovaquie',
        '99254': u'Chypre',
        '99136': u'Irlande',
        '99122': u'Pologne',
        '99145': u'Slovénie',
        '99101': u'Danemark',
        '99127': u'Italie',
        '99139': u'Portugal',
        '99104': u'Suède',
        '99134': u'Espagne',
        '99107': u'Lettonie',
        '99700': u'UE Hors France',
        '99702': u'Amérique du Nord',
        '99715': u'Afrique',
        '99711': u'Océanie',
        '99701': u'Europe Hors UE',
        '99714': u'Amérique Latine',
        '99716': u'Asie',
    }.iteritems())])

    fonction_choices = OrderedDict([(k, u'%s' % (v)) for k, v in sorted({
        ' ': u'-- Indifférent --',
        '101828': u'Commercial, Marketing',
        '101782': u'.....Administration des ventes et SAV',
        '101783': u'.....Chargé d\'affaires, technico-commercial',
        '101784': u'.....Commercial',
        '101785': u'.....Commerce international',
        '101786': u'.....Direction commerciale et marketing',
        '101787': u'.....Direction régionale et d\'agence',
        '101788': u'.....Marketing',
        '101789': u'.....Ventes en magasin',
        '101829': u'Communication, Création',
        '101790': u'.....Communication',
        '101791': u'.....Création',
        '101792': u'.....Documentation, rédaction technique',
        '101793': u'.....Journalisme, édition',
        '101830': u'Direction d\'entreprise',
        '101794': u'.....Adjoint, conseil de direction',
        '101795': u'.....Direction générale',
        '101831': u'Etudes, Recherche et Développement',
        '101796': u'.....Conception, recherche',
        '101797': u'.....Direction recherche et développement',
        '101798': u'.....Etudes socio-économiques',
        '101799': u'.....Projets scientifiques et techniques',
        '101800': u'.....Test, essai, validation, expertise',
        '101832': u'Gestion, Finance, Administration',
        '101801': u'.....Administration, gestion, organisation',
        '101802': u'.....Comptabilité',
        '101803': u'.....Contrôle de gestion, audit',
        '101804': u'.....Direction gestion, finance',
        '101805': u'.....Droit, fiscalité',
        '101806': u'.....Finance, trésorerie',
        '101833': u'Informatique',
        '101807': u'.....Direction informatique',
        '101808': u'.....Exploitation, maintenance informatique',
        '101809': u'.....Informatique de gestion',
        '101810': u'.....Informatique industrielle',
        '101811': u'.....Informatique web, sites et portails Internet',
        '101812': u'.....Maîtrise d\'ouvrage et fonctionnel',
        '101813': u'.....Système, réseaux, données',
        '101834': u'Production Industrielle, Travaux, Chantiers',
        '101814': u'.....Cadres de chantier',
        '101815': u'.....Cadres de production industrielle',
        '101816': u'.....Direction d\'unité industrielle',
        '101835': u'Ressources Humaines',
        '101817': u'.....Administration des RH',
        '101818': u'.....Développement des RH',
        '101819': u'.....Direction des ressources humaines',
        '101820': u'.....Formation initiale et continue',
        '101836': u'Sanitaire, Social, Culture',
        '101821': u'.....Activités sanitaires, sociales et culturelles',
        '101837': u'Services Techniques',
        '101822': u'.....Achats',
        '101823': u'.....Direction des services techniques',
        '101824': u'.....Logistique',
        '101825': u'.....Maintenance, sécurité',
        '101826': u'.....Process, méthodes',
        '101827': u'.....Qualité',
    }.iteritems())])

    secteur_choices = OrderedDict([(k, u'%s' % (v)) for k, v in sorted({
        ' ': u'-- Indifférent --',
        '101752': u'Activités des organisations associatives et administration publique',
        '101753': u'Activités informatiques',
        '101754': u'Activités juridiques et comptables',
        '101755': u'Agroalimentaire',
        '101756': u'Automobile, aéronautique et autres matériels de transport',
        '101757': u'Banque et Assurances',
        '101758': u'Bois - Papier - Imprimerie',
        '101759': u'Chimie - Caoutchouc - Plastique',
        '101760': u'Commerce interentreprises',
        '101761': u'Communication et médias',
        '101762': u'Conseil et gestion des entreprises',
        '101763': u'Construction',
        '101764': u'Distribution généraliste et spécialisée',
        '101765': u'Energies - Eau',
        '101766': u'Equipements électriques et électroniques',
        '101767': u'Formation initiale et continue',
        '101768': u'Gestion des déchets',
        '101769': u'Hôtellerie - Restauration - Loisirs',
        '101770': u'Immobilier',
        '101771': u'Industrie pharmaceutique',
        '101772': u'Ingénierie - R et D',
        '101773': u'Intermédiaires du recrutement',
        '101774': u'Mécanique - Métallurgie',
        '101775': u'Meuble, Textile et autres industries manufacturières',
        '101776': u'Santé - action sociale',
        '101777': u'Services divers aux entreprises',
        '101778': u'Télécommunications',
        '101779': u'Transports et logistique',
    }.iteritems())])

    type_contrat_choices = OrderedDict([(k, u'%s' % (v)) for k, v in sorted({
        ' ': u'-- Indifférent --',
        '101888': u'CDI',
        '101887': u'CDD',
        '101889': u'Travail Temporaire',
    }.iteritems())])

    salary_choices = OrderedDict([(k, u'%s' % (v)) for k, v in sorted({
        ' ': u'-- Indifférent --',
        '101839': u'Moins de 35 K€',
        '101840': u'Entre 35 et 49 K€',
        '101841': u'Entre 50 et 69 K€',
        '101842': u'Entre 70 et 90 K€',
        '101843': u'Plus de 90 K€',
    }.iteritems())])

    date_choices = OrderedDict([(k, u'%s' % (v)) for k, v in sorted({
        ' ': u'-- Indifférent --',
        '101850': u'Aujourd\'hui',
        '101851': u'Les 7 derniers jours',
        '101852': u'Les 30 derniers jours',
        '101853': u'Toutes les offres',
    }.iteritems())])

    level_choices = OrderedDict([(k, u'%s' % (v)) for k, v in sorted({
        ' ': u'-- Indifférent --',
        '101846': u'Débutant',
        '101848': u'Expérimenté',
    }.iteritems())])

    CONFIG = BackendConfig(Value('place', label=u'Lieu', choices=places_choices, default=''),
                           Value('fonction', label=u'Fonction', choices=fonction_choices, default=''),
                           Value('secteur', label=u'Secteur', choices=secteur_choices, default=''),
                           Value('contrat', label=u'Contrat', choices=type_contrat_choices, default=''),
                           Value('salaire', label=u'Salaire', choices=salary_choices, default=''),
                           Value('limit_date', label=u'Date', choices=date_choices, default=''),
                           Value('level', label=u'Expérience', choices=level_choices, default=''))

    def search_job(self, pattern=None):
        with self.browser:
            for job_advert in self.browser.search_job(pattern=pattern):
                yield job_advert

    def advanced_search_job(self):
        for job_advert in self.browser.advanced_search_job(region=self.config['place'].get(),
                                                           fonction=self.config['fonction'].get(),
                                                           secteur=self.config['secteur'].get(),
                                                           salaire=self.config['salaire'].get(),
                                                           contrat=self.config['contrat'].get(),
                                                           limit_date=self.config['limit_date'].get(),
                                                           level=self.config['level'].get()):
            yield job_advert

    def get_job_advert(self, _id, advert=None):
        with self.browser:
            return self.browser.get_job_advert(_id, advert)

    def fill_obj(self, advert, fields):
        self.get_job_advert(advert.id, advert)

    OBJECTS = {ApecJobAdvert: fill_obj}
