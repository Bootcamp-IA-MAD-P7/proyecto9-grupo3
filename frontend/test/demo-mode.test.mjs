import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import { URL } from 'node:url';
import { DEMO_COMMENTS, filterAndSortComments, resetDemoComments } from '../src/demo/demoLogic.ts';

const demoSource = await readFile(new URL('../src/components/DemoPage.tsx', import.meta.url), 'utf8');
const appSource = await readFile(new URL('../src/App.tsx', import.meta.url), 'utf8');

test('public demo is separate from authenticated moderator access', () => {
  assert.match(appSource, /window\.location\.pathname === '\/demo'/);
  assert.match(appSource, /window\.location\.pathname !== '\/moderator'/);
  assert.match(demoSource, /loadYouTubeComments/);
  assert.match(demoSource, /datos de ejemplo/i);
  assert.match(demoSource, /YouTube Data API/);
});

test('synthetic data is broad and resettable', () => {
  assert.ok(DEMO_COMMENTS.length >= 8);
  assert.ok(DEMO_COMMENTS.every((comment) => comment.author.startsWith('Cuenta_demo_')));
  assert.ok(DEMO_COMMENTS.every((comment) => comment.score_source === 'SIMULATED'));
  assert.ok(new Set(DEMO_COMMENTS.map((comment) => comment.status)).size >= 3);
  assert.ok(filterAndSortComments(DEMO_COMMENTS, 'PENDING', 'RISK_DESC').every((comment) => comment.status !== 'REVIEWED'));
  assert.ok(filterAndSortComments(DEMO_COMMENTS, 'REVIEWED', 'RISK_DESC').every((comment) => comment.status === 'REVIEWED'));
  const reset = resetDemoComments();
  assert.notEqual(reset, DEMO_COMMENTS);
  assert.deepEqual(reset, DEMO_COMMENTS);
  assert.match(demoSource, /aria-pressed/);
});
