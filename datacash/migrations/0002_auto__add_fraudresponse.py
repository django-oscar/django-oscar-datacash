# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'FraudResponse'
        db.create_table('datacash_fraudresponse', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('aggregator_identifier', self.gf('django.db.models.fields.CharField')(max_length=15, blank=True)),
            ('merchant_identifier', self.gf('django.db.models.fields.CharField')(max_length=15)),
            ('merchant_order_ref', self.gf('django.db.models.fields.CharField')(max_length=250, db_index=True)),
            ('t3m_id', self.gf('django.db.models.fields.CharField')(unique=True, max_length=128)),
            ('score', self.gf('django.db.models.fields.IntegerField')()),
            ('recommendation', self.gf('django.db.models.fields.IntegerField')()),
            ('message_digest', self.gf('django.db.models.fields.CharField')(max_length=128, blank=True)),
            ('raw_response', self.gf('django.db.models.fields.TextField')()),
            ('date_created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal('datacash', ['FraudResponse'])


    def backwards(self, orm):
        # Deleting model 'FraudResponse'
        db.delete_table('datacash_fraudresponse')


    models = {
        'datacash.fraudresponse': {
            'Meta': {'object_name': 'FraudResponse'},
            'aggregator_identifier': ('django.db.models.fields.CharField', [], {'max_length': '15', 'blank': 'True'}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'merchant_identifier': ('django.db.models.fields.CharField', [], {'max_length': '15'}),
            'merchant_order_ref': ('django.db.models.fields.CharField', [], {'max_length': '250', 'db_index': 'True'}),
            'message_digest': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'}),
            'raw_response': ('django.db.models.fields.TextField', [], {}),
            'recommendation': ('django.db.models.fields.IntegerField', [], {}),
            'score': ('django.db.models.fields.IntegerField', [], {}),
            't3m_id': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '128'})
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