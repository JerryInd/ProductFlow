UPDATE pipeline_sources SET group_id='120363166742058584@g.us' WHERE pipeline_id=11 AND group_id='120363166228326290@g.us';
UPDATE groups SET group_id='120363166742058584@g.us' WHERE group_id='120363166228326290@g.us';
SELECT 'pipeline_sources:' || count(*) FROM pipeline_sources WHERE pipeline_id=11;
SELECT 'groups:' || group_id || '=' || group_name FROM groups WHERE group_name LIKE '%Rizwan%';
