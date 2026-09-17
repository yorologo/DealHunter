import pytest

from tests.helpers.db import insert_membership, insert_product, insert_store


def test_merchant_location_mapping_requires_explicit_confirmation(current_schema_db):
    from dealhunter.reviewed_mappings import confirm_merchant_location, list_unresolved_listings

    insert_store(current_schema_db, 'raw-1', name='Same Name', provider='rappi')
    current_schema_db.commit()
    unresolved = list_unresolved_listings(current_schema_db, provider='rappi')
    assert unresolved == [{
        'provider': 'rappi', 'store_id': 'raw-1', 'name': 'Same Name',
        'merchant_id': None, 'location_id': None, 'status': 'UNRESOLVED',
    }]

    confirm_merchant_location(
        current_schema_db,
        provider='rappi', store_id='raw-1',
        merchant_id='m-1', merchant_name='Merchant',
        location_id='loc-1', location_name='Branch',
    )
    row = current_schema_db.execute(
        "SELECT provider,store_id,merchant_id,location_id FROM stores WHERE provider='rappi' AND store_id='raw-1'"
    ).fetchone()
    assert row == ('rappi', 'raw-1', 'm-1', 'loc-1')


def test_merchant_mapping_never_merges_same_display_name_automatically(current_schema_db):
    from dealhunter.reviewed_mappings import confirm_merchant_location

    insert_store(current_schema_db, 'a', name='Duplicated', provider='rappi')
    insert_store(current_schema_db, 'b', name='Duplicated', provider='uber_eats')
    current_schema_db.commit()
    confirm_merchant_location(
        current_schema_db, provider='rappi', store_id='a',
        merchant_id='m-a', merchant_name='Merchant A',
        location_id='loc-a', location_name='A',
    )
    row = current_schema_db.execute(
        "SELECT merchant_id,location_id FROM stores WHERE provider='uber_eats' AND store_id='b'"
    ).fetchone()
    assert row == (None, None)


def test_conflicting_authoritative_merchant_mapping_fails_closed(current_schema_db):
    from dealhunter.reviewed_mappings import confirm_merchant_location

    insert_store(current_schema_db, 'raw-1', provider='rappi')
    current_schema_db.commit()
    confirm_merchant_location(
        current_schema_db, provider='rappi', store_id='raw-1',
        merchant_id='m-1', merchant_name='Merchant', location_id='l-1', location_name='One',
    )
    with pytest.raises(ValueError, match='already mapped'):
        confirm_merchant_location(
            current_schema_db, provider='rappi', store_id='raw-1',
            merchant_id='m-2', merchant_name='Other', location_id='l-2', location_name='Two',
        )


def test_browse_mapping_is_explicit_and_unmapped_remains_unclassified(current_schema_db):
    from dealhunter.reviewed_mappings import add_browse_node, confirm_browse_mapping, list_unclassified_memberships

    insert_store(current_schema_db, 's1', provider='rappi')
    insert_product(current_schema_db, 'p1', 's1', provider='rappi')
    insert_membership(
        current_schema_db, 's1', 'p1', 'aisle', 'Bebidas',
        path='["Super", "Bebidas"]', source='provider', provider='rappi',
    )
    current_schema_db.commit()

    rows = list_unclassified_memberships(current_schema_db, provider='rappi')
    assert rows[0]['status'] == 'UNCLASSIFIED'
    assert rows[0]['raw_name'] == 'Bebidas'

    add_browse_node(current_schema_db, 'drinks', name='Bebidas', level='CATEGORY')
    confirm_browse_mapping(
        current_schema_db, provider='rappi', raw_type='aisle', raw_name='Bebidas',
        raw_path='["Super", "Bebidas"]', browse_node_id='drinks',
    )
    assert list_unclassified_memberships(current_schema_db, provider='rappi') == []


def test_browse_mapping_ambiguity_is_rejected(current_schema_db):
    from dealhunter.reviewed_mappings import add_browse_node, confirm_browse_mapping

    add_browse_node(current_schema_db, 'drinks', name='Bebidas', level='CATEGORY')
    add_browse_node(current_schema_db, 'promo', name='Promos', level='CATEGORY')
    confirm_browse_mapping(
        current_schema_db, provider='rappi', raw_type='aisle', raw_name='Bebidas',
        raw_path='[]', browse_node_id='drinks',
    )
    with pytest.raises(ValueError, match='already maps'):
        confirm_browse_mapping(
            current_schema_db, provider='rappi', raw_type='aisle', raw_name='Bebidas',
            raw_path='[]', browse_node_id='promo',
        )


def test_mapping_cli_contracts_are_explicit():
    from dealhunter.cli import build_parser
    parser = build_parser()

    args = parser.parse_args([
        'commerce-map', 'confirm', '--provider', 'rappi', '--store-id', 's1',
        '--merchant-id', 'm1', '--merchant-name', 'Merchant',
        '--location-id', 'l1', '--location-name', 'Branch',
    ])
    assert args.command == 'commerce-map'
    assert args.action == 'confirm'

    args = parser.parse_args([
        'browse-map', 'confirm', '--provider', 'rappi', '--raw-type', 'aisle',
        '--raw-name', 'Bebidas', '--raw-path', '[]', '--browse-node-id', 'drinks',
    ])
    assert args.command == 'browse-map'
    assert args.action == 'confirm'
