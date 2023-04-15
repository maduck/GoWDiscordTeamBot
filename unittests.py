import unittest

from data_source import PetContainer, Pets


class PetTests(unittest.TestCase):
    def setUp(self):
        user_data = {'pEconomyModel': {'PetEffects': []}}
        pet_data = '[{"Effect": 0, "FileBase": "Pet_000", "Id": 13000, "KingdomId": 3036, ' \
                   '"ManaColors": {"ColorBlue": true}, "Name": "[Pet_000_NAME]", "ReferenceName": "Crabbie"},' \
                   '{"Effect": 2, "EffectData": 3067, "FileBase": "Pet_111", "Id": 13111, "KingdomId": 3023,' \
                   ' "LockedHelpText": "FACTION", "ManaColors": {"ColorYellow": true}, "Name": "",' \
                   ' "ReferenceName": "BinChicken"}]'
        self.pets = Pets.from_json(pet_data, user_data=user_data)

    def test_class(self):
        self.assertIsInstance(self.pets[13000], PetContainer)

    def test_id(self):
        self.assertEqual(self.pets[13000].id, 13000)

    def test_reference_name_replacement(self):
        self.assertEqual(self.pets[13111]['en'].name,
                         self.pets[13111]['en'].reference_name)

    def test_matching(self):
        self.assertTrue(self.pets[13000].matches_precisely('crabbie', 'en'))
        self.assertTrue(self.pets[13111].matches('bIn     chIckEn', 'en'))

    def test_search(self):
        search_result = self.pets.search('13000', 'en')
        self.assertEqual(len(search_result), 1)
        self.assertDictEqual(search_result[0].data, self.pets[13000]['en'].data)


if __name__ == '__main__':
    unittest.main()
