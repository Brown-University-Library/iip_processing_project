# -*- coding: utf-8 -*-

""" Contains travis-ci.org friendly tests. """

import base64, json, logging, os
from django.test import TestCase
from iip_processing_app.lib.github_helper import GHHelper, GHValidator
from iip_processing_app.lib.processor import Prepper, StatusBackupper


log = logging.getLogger(__name__)
TestCase.maxDiff = None
gh_helper = GHHelper()
gh_validator = GHValidator()
stts_bckppr = StatusBackupper()
prepper = Prepper()


class RootUrlTest(TestCase):
    """ Checks root urls. """

    def setUp(self):
        pass

    def test_root_url_no_slash(self):
        """ Checks '/root_url'. """
        response = self.client.get( '' )  # project root part of url is assumed
        self.assertEqual( 302, response.status_code )  # permanent redirect
        redirect_url = response._headers['location'][1]
        self.assertEqual(  '/info/', redirect_url )

    def test_root_url_slash(self):
        """ Checks '/root_url/'. """
        response = self.client.get( '/' )  # project root part of url is assumed
        self.assertEqual( 302, response.status_code )  # permanent redirect
        redirect_url = response._headers['location'][1]
        self.assertEqual(  '/info/', redirect_url )


class GHValidatorTest(TestCase):
    """ Checks code handling incoming info. """

    def setUp(self):
        pass

    def test_parse_http_basic_auth(self):
        """ Checks parsing of username and password. """
        userpass_utf8 = '{usrnm}:{psswd}'.format( usrnm='username_foo', psswd='password_bar' ).encode( 'utf-8' )
        log.debug( f'userpass_utf8, ``{userpass_utf8}``' )

        b64_utf8_a = base64.encodebytes( userpass_utf8 )
        assert type(b64_utf8_a) == bytes, type(b64_utf8_a)

        b64_a = b64_utf8_a.decode( 'utf-8' )
        b64_b = b64_a.replace( '\n', '' )
        log.debug( f'b64_b, ``{b64_b}``' )

        basic_auth_string = f'Basic {b64_b}'
        log.debug( f'basic_auth_string, ``{basic_auth_string}``' )
        self.assertEqual(
            { 'received_username': 'username_foo', 'received_password': 'password_bar' },
            gh_validator.parse_http_basic_auth( basic_auth_string )
        )

    # def test_parse_http_basic_auth(self):
    #     """ Checks parsing of username and password. """
    #     encoded_string = base64.encodestring( '{usrnm}:{psswd}'.format(usrnm='username_foo', psswd='password_bar') ).replace( '\n', '' )
    #     basic_auth_string = 'Basic {}'.format( encoded_string )
    #     log.debug( 'basic_auth_string, ```{}```'.format(basic_auth_string) )
    #     self.assertEqual(
    #         { 'received_username': 'username_foo', 'received_password': 'password_bar' },
    #         gh_validator.parse_http_basic_auth( basic_auth_string )
    #     )

    def test_parse_signature(self):
        """ Checks parsing of github's X-Hub-Signature header.
            Note: hmac requires a byte-string secret. """
        dummy_secret = 'foo_secret'
        dummy_payload = json.dumps({ 'foo': 'bar' })
        dummy_signature = 'sha1=6ef7bc87b6a827c49de558766f2229f8d3e5e81c'
        log.debug( 'type(dummy_signature), ```{}```'.format(type(dummy_signature)) )
        self.assertEqual(
            dummy_signature,
            gh_validator.determine_signature( dummy_secret, dummy_payload  )
        )


class GitHubResponseParseTest(TestCase):
    """ Checks github response parsing. """

    def setUp(self):
        pass

    def test_examine_commits(self):
        """ Checks extraction of files to process. """
        commits_list = json.loads('''[
            {
              "added": [],
              "author": {
                "email": "aaa@aaa.edu",
                "name": "First Last",
                "username": "first"
              },
              "committer": {
                "email": "noreply@github.com",
                "name": "GitHub",
                "username": "web-flow"
              },
              "distinct": true,
              "id": "88cb3c31a7bcec4adc0558fbff74347d0a9245e1",
              "message": "test commit of comment.",
              "modified": [
                "epidoc-files/abur0001.xml",
                "blah",
                "epidoc-files/aaa123.xml"
              ],
              "removed": [],
              "timestamp": "2017-01-19T11:00:30-05:00",
              "tree_id": "e45afe1e50d17e94e9bc2a26a35f4b3f3457bb55",
              "url": "https://github.com/Brown-University-Library/iip-texts/commit/88cb3c31a7bcec4adc0558fbff74347d0a9245e1"
            }
          ]''')
        self.assertEqual(
            ( [], [u'aaa123', u'abur0001'], [] ),  # added, modified, removed
            gh_helper.examine_commits( commits_list )
        )


class StatusBackupperTest(TestCase):
    """ Checks status-backup code. """

    def test_parse_solr_response(self):
        response_dct = {
            u'response': {
                u'docs': [
                    {u'display_status': u'approved', u'inscription_id': u'masa481'},
                    {u'display_status': u'approved', u'inscription_id': u'abur0001'},
                    {u'display_status': u'approved', u'inscription_id': u'akas0002'},
                    {u'display_status': u'approved', u'inscription_id': u'ahma0001'},
                    {u'display_status': u'approved', u'inscription_id': u'abil0001'},
                    {u'display_status': u'to_correct', u'inscription_id': u'ahma0003'},
                    {u'display_status': u'approved', u'inscription_id': u'akas0001'},
                    {u'display_status': u'to_approve', u'inscription_id': u'tdor0004'}],
                u'numFound': 8,
                u'start': 0},
            u'responseHeader': {
                u'QTime': 2,
                u'params': {
                    u'fl': u'inscription_id,display_status',
                    u'indent': u'true',
                    u'q': u'*:*',
                    u'rows': u'6000',
                    u'wt': u'json'},
                u'status': 0}
        }
        self.assertEqual(
            {
                u'counts': {
                    u'approved': 6, u'to_approve': 1, u'to_correct': 1, u'total': 8},
                u'statuses': {
                    u'abil0001': u'approved',
                    u'abur0001': u'approved',
                    u'ahma0001': u'approved',
                    u'ahma0003': u'to_correct',
                    u'akas0001': u'approved',
                    u'akas0002': u'approved',
                    u'masa481': u'approved',
                    u'tdor0004': u'to_approve'}
            },
            stts_bckppr.make_status_dct( response_dct )
        )

    ## end class StatusBackupperTest()


class PrepperUnitTest(TestCase):
    """ Checks travis-friendly processor.py functions. """

    def setUp(self):
        self.xml_dir = os.environ['IIP_PRC__CLONED_INSCRIPTIONS_PATH']

    def test_update_status(self):
        """ Checks addition of display_status. """
        display_status = 'foo'
        initial_solr_xml = '''<?xml version="1.0" encoding="UTF-8"?><add><doc><field name="inscription_id">abur0001</field><field name="region">Judaea</field><field name="city">Bethennim</field><field name="placeMenu">Bethennim  (Judaea)</field><field name="placeMenu">Judaea</field><field name="place_found">[Bethennim, Judaea. Room A in church. ]
Judaea. Bethennim (Khirbet Abu Rish), in the church complex, Room A.
</field><field name="notAfter">0700</field><field name="notBefore">0300</field><field name="type">invocation</field><field name="language">grc</field><field name="language_display">Greek</field><field name="religion">christian</field><field name="physical_type">mosaic</field><field name="figure_desc">square mosaic</field><field name="transcription">&lt;span&gt;

               Κύριε
               [
                  Ἰησοῦ
                  Χριστέ μνήσθητ]ι &lt;br/&gt;το[ῦ δούλου σου [-----]
               ]ά&lt;br/&gt;λα[-----]
               [τοῦ]
               &lt;br/&gt;πρε[σβυτέρου καί π]άν-&lt;br/&gt;των [τῶν π]ροσκυ-&lt;br/&gt;νούντων ἐν τῴ&lt;br/&gt;τόπῳ τούτῳ καί&lt;br/&gt;τῶν καρποφο-&lt;br/&gt;ρούντων ἐν τῷ&lt;br/&gt;τόπῳ τούτῳ

&lt;/span&gt;

    </field><field name="transcription_search">

               Κε Κύριε

                  Ἰῦ Ἰησοῦ
                  Χέ Χριστέ μνήσθητι τοῦ δούλου σου
               άλα
               τοῦ
               πρεσβυτέρου καί πάν-των τῶν προσκυ-νούντων ἐν τῴτόπῳ τούτῳ καίτῶν καρποφο-ρούντων ἐν τῷτόπῳ τούτῳ
         </field><field name="translation">Lord Jesus Christ [remember your servant ...] the priest and all the pilgrims to
                    this place [or: all those who pray in this place] and those who contribute to
                    this place.</field><field name="translation_search">
            Lord Jesus Christ [remember your servant ...] the priest and all the pilgrims to
                    this place [or: all those who pray in this place] and those who contribute to
                    this place.
         </field><field name="diplomatic">&lt;span&gt;
            ΚΕ [ΙΥ ΧΕ ΜΝΗΣΘΗΤ]Ι&lt;br/&gt;ΤΟ[Υ ΔΟΥΛΟΥ ΣΟΥ] Α&lt;br/&gt;ΛΑ [-----]
               [ΤΟΥ]
               &lt;br/&gt;ΠΡΕ[ΣΒΥΤΕΡΟΥ ΚΑΙ Π]ΑΝ-&lt;br/&gt;ΤΩΝ [ΤΩΝ Π]ΡΟΣΚΥ-&lt;br/&gt;ΝΟΥΝΤΩΝ ΕΝ ΤΩ&lt;br/&gt;ΤΟΠΩ ΤΟΥΤΩ ΚΑΙ&lt;br/&gt;ΤΩΝ ΚΑΡΠΟΦΟ-&lt;br/&gt;ΡΟΥΝΤΩΝ ΕΝ ΤΩ&lt;br/&gt;ΤΟΠΩ ΤΟΥΤΩ

&lt;/span&gt;

    </field><field name="dimensions">h: 1 m; w: 1 m; d: unknown; let: N/A</field><field name="bibl">bibl=IIP-487.xml|nType=page|n=147-148</field><field name="bibl">bibl=IIP-544.xml|nType=page|n=339-358</field><field name="biblDiplomatic">bibl=IIP-487.xml|nType=page|n=147-148</field><field name="biblTranscription">bibl=IIP-487.xml|nType=page|n=147-148</field><field name="biblTranslation">bibl=IIP-487.xml|nType=page|n=147-148</field><field name="short_description">Bethennim (Khirbet Abu Rish). 300-700 CE. Mosaic in a square frame. Invocation.</field><field name="description">
            The mosaic was discovered in the earliest structure (Room A) of the church complex at Khirbet Abu Rish, a site nestled in the 'Anun valley, which separates the Hebron Mountains from the Judean Desert. The church complex comprises a large courtyard, water cisterns, wine-pressing installations, and several tombs. The sides of the mosaic in Room A are all one meter in length. The framed inscription is situated in the center of the mosaic. The letters are made out of black stones and placed on a white background. The inscription does not have spelling or grammatical errors. The only abbreviation used was that of the sacra nomina, or the sacred name, in the first line. The first five lines of the inscription are damaged. The text is a supplication, in which a person asks a supernatural deity to provide something. The individual who wrote the inscription is asking Jesus to remember a person who has passed away, whose name has not been preserved, and he/she is also asking for the remembrance of those who pray and contribute to this place. The inscription therefore showcases the significance of this place for Christians.
         </field></doc></add>'''
        updated_xml = prepper.update_status( display_status, initial_solr_xml )
        self.assertEqual(
            True,
            '<field name="display_status">foo</field>' in updated_xml
        )

    ## end class PrepperUnitTest()
