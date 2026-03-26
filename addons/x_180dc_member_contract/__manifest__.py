{
    'name': '180DC Member Contract',
    'summary': 'Native-first membership timeline on contracts',
    'version': '18.0.1.1.0',
    'category': 'Human Resources',
    'license': 'LGPL-3',
    'depends': ['hr', 'hr_contract', 'hr_work_entry_contract'],
    'data': [
        'data/contract_type_data.xml',
        'views/hr_contract_views.xml',
    ],
    'installable': True,
    'application': False,
}
