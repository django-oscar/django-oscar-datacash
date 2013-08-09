# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Removing unique constraint on 'FraudResponse', fields ['t3m_id']
        db.delete_unique('datacash_fraudresponse', ['t3m_id'])

        # Adding index on 'FraudResponse', fields ['t3m_id']
        db.create_index('datacash_fraudresponse', ['t3m_id'])


    def backwards(self, orm):
        # Removing index on 'FraudResponse', fields ['t3m_id']
        db.delete_index('datacash_fraudresponse', ['t3m_id'])

        # Adding unique constraint on 'FraudResponse', fields ['t3m_id']
        db.create_unique('datacash_fraudresponse', ['t3m_id'])


    models = {
        'datacash.fraudresponse': {
            'Meta': {'ordering': "('-date_created',)", 'object_name': 'FraudResponse'},
            'aggregator_identifier': ('django.db.models.fields.CharField', [], {'max_length': '15', 'blank': 'True'}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'merchant_identifier': ('django.db.models.fields.CharField', [], {'max_length': '15'}),
            'merchant_order_ref': ('django.db.models.fields.CharField', [], {'max_length': '250', 'db_index': 'True'}),
            'message_digest': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'}),
            'raw_response': ('django.db.models.fields.TextField', [], {}),
            'recommendation': ('django.db.models.fields.IntegerField', [], {}),
            'score': ('django.db.models.fields.IntegerField', [], {}),
            't3m_id': ('django.db.models.fields.CharField', [], {'max_length': '128', 'db_index': 'True'})
        },
        'datacash.ordertransaction': {
            'Meta': {'ordering': "('-date_created',)", 'object_name': 'OrderTransaction'},
            'amount': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '12', 'decimal_places': '2', 'blank': 'True'}),
            'auth_code': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'datacash_reference': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'merchant_reference': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'method': ('django.db.models.fields.CharField', [], {'max_length': '12'}),
            'order_number': ('django.db.models.fields.CharField', [], {'max_length': '128', 'db_index': 'True'}),
            'reason': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'request_xml': ('django.db.models.fields.TextField', [], {}),
            'response_xml': ('django.db.models.fields.TextField', [], {}),
            'status': ('django.db.models.fields.PositiveIntegerField', [], {})
        }
    }

    complete_apps = ['datacash']