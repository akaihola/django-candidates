# -*- coding: utf-8 -*-

from nose.tools import eq_, assert_true, assert_false

from candidates.utils.users import (
    noncombining, remove_diacritics, slugify, usernameize, generate_username)

def test_noncombining():
    from unicodedata import normalize
    eq_(normalize('NFKD', 'ä'.decode('UTF-8')), u'a\u0308')
    assert_true(noncombining(u'a'))
    assert_false(noncombining(u'\u0308'))

def test_remove_diacritics():
    eq_(remove_diacritics('áÖèůçŷṫŠ'), 'aOeucytS')
    eq_(remove_diacritics('áÖèůçŷṫŠ'.decode('UTF-8')), u'aOeucytS')

def test_slugify():
    eq_(slugify(u'M\xe4rta'), 'marta')

def test_usernameize():
    eq_(usernameize("Liisa O'Malley-Järvinen".decode('UTF-8')),
        u'liisaomalleyjarvinen')

def test_generate_username():
    round_name = '2009'
    eq_(generate_username('Bo', 'Ek', round_name), 'boek2009')
    eq_(generate_username('Bo', 'Ek', round_name, 55), 'boek2009_55')
    eq_(generate_username(
            u'Erkki-Aino-Maija-M\xe4rta',
            u'Nummelan-Pusulan-\xc4rj\xe4v\xf6isen-Sepp\xe4l\xe4',
            round_name,
            4),
        'erkkiainomaijamartanumme2009_4')
