-- Adds coordinates so venues can be sorted by distance from a visitor.
alter table venues add column if not exists lat double precision;
alter table venues add column if not exists lng double precision;
