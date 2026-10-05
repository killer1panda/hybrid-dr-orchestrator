-- infra/onprem/cdc/setup_logical_replication.sql
-- Establishes Logical Replication Publication and CDC Replication Slot
-- for real-time transactional stream capture into secondary DR targets.

-- 1. Create publication for tables
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_publication WHERE pubname = 'dr_cdc_publication'
    ) THEN
        CREATE PUBLICATION dr_cdc_publication FOR ALL TABLES;
        RAISE NOTICE 'Publication dr_cdc_publication created successfully.';
    ELSE
        RAISE NOTICE 'Publication dr_cdc_publication already exists.';
    END IF;
END $$;

-- 2. Create logical replication slot (using test_decoding output plugin)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_replication_slots WHERE slot_name = 'dr_cdc_slot'
    ) THEN
        PERFORM pg_create_logical_replication_slot('dr_cdc_slot', 'test_decoding');
        RAISE NOTICE 'Logical replication slot dr_cdc_slot created successfully.';
    ELSE
        RAISE NOTICE 'Logical replication slot dr_cdc_slot already exists.';
    END IF;
END $$;
