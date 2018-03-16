CREATE KEYSPACE IF NOT EXISTS "metrics" WITH REPLICATION = {
	'class' : 'NetworkTopologyStrategy',
	'ASH2' : 2,
	'PHX2' : 2
  };
use metrics;
CREATE TABLE IF NOT EXISTS Octets (
        host text,
	metric text,
        date int,
	time timestamp,
	type text,
	value double,
	PRIMARY KEY(date,host,time,metric)
) WITH gc_grace_seconds=259200;
CREATE TABLE IF NOT EXISTS Packets (
        host text,
	metric text,
        date int,
	time timestamp,
	type text,
	value double,
	PRIMARY KEY(date,host,time,metric)
) WITH gc_grace_seconds=259200;
CREATE TABLE IF NOT EXISTS Errors (
        host text,
	metric text,
        date int,
	time timestamp,
	type text,
	value double,
	PRIMARY KEY(date,host,time,metric)
) WITH gc_grace_seconds=259200;
CREATE TABLE IF NOT EXISTS metrics_index (
  host text,
  group text,
  metric text,
  PRIMARY KEY (host, group)
) WITH gc_grace_seconds=259200;
CREATE TABLE IF NOT EXISTS Octets1800 (
        host text,
	metric text,
        date int,
	time timestamp,
	type text,
	avg double,
	min double,
	max double,
	PRIMARY KEY(date,host,time,metric)
) WITH gc_grace_seconds=259200;
CREATE TABLE IF NOT EXISTS Packets1800 (
        host text,
	metric text,
        date int,
	time timestamp,
	type text,
	avg double,
	min double,
	max double,
	PRIMARY KEY(date,host,time,metric)
) WITH gc_grace_seconds=259200;
CREATE TABLE IF NOT EXISTS Errors1800 (
        host text,
	metric text,
        date int,
	time timestamp,
	type text,
	avg double,
	min double,
	max double,
	PRIMARY KEY(date,host,time,metric)
) WITH gc_grace_seconds=259200;
CREATE TABLE IF NOT EXISTS rollups1800_index (
  host text,
  group text,
  metric text,
  PRIMARY KEY (host, group)
) WITH gc_grace_seconds=259200;
CREATE TABLE IF NOT EXISTS Octets7200 (
        host text,
	metric text,
        date int,
	time timestamp,
	type text,
	avg double,
	min double,
	max double,
	PRIMARY KEY(date,host,time,metric)
) WITH gc_grace_seconds=259200;
CREATE TABLE IF NOT EXISTS Packets7200 (
        host text,
	metric text,
        date int,
	time timestamp,
	type text,
	avg double,
	min double,
	max double,
	PRIMARY KEY(date,host,time,metric)
) WITH gc_grace_seconds=259200;
CREATE TABLE IF NOT EXISTS Errors7200 (
        host text,
	metric text,
        date int,
	time timestamp,
	type text,
	avg double,
	min double,
	max double,
	PRIMARY KEY(date,host,time,metric)
) WITH gc_grace_seconds=259200;
CREATE TABLE IF NOT EXISTS rollups7200_index (
  host text,
  group text,
  metric text,
  PRIMARY KEY (host, group)
) WITH gc_grace_seconds=259200;
CREATE TABLE IF NOT EXISTS Octets86400 (
        host text,
	metric text,
        date int,
	time timestamp,
	type text,
	avg double,
	min double,
	max double,
	PRIMARY KEY(date,host,time,metric)
) WITH gc_grace_seconds=259200;
CREATE TABLE IF NOT EXISTS Packets86400 (
        host text,
	metric text,
        date int,
	time timestamp,
	type text,
	avg double,
	min double,
	max double,
	PRIMARY KEY(date,host,time,metric)
) WITH gc_grace_seconds=259200;
CREATE TABLE IF NOT EXISTS Errors86400 (
        host text,
	metric text,
        date int,
	time timestamp,
	type text,
	avg double,
	min double,
	max double,
	PRIMARY KEY(date,host,time,metric)
) WITH gc_grace_seconds=259200;
CREATE TABLE IF NOT EXISTS rollups86400_index (
  host text,
  group text,
  metric text,
  PRIMARY KEY (host, metric)
) WITH gc_grace_seconds=259200;
