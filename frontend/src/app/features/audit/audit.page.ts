import { ChangeDetectionStrategy, Component, OnInit, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { firstValueFrom } from 'rxjs';

import { ApiService, errorMessage } from '../../core/api';
import { AuditLog, Page } from '../../core/models';

@Component({
  selector: 'app-audit-page',
  imports: [ReactiveFormsModule],
  templateUrl: './audit.page.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AuditPage implements OnInit {
  private readonly api = inject(ApiService);
  private readonly fb = inject(FormBuilder);

  readonly logs = signal<AuditLog[]>([]);
  readonly total = signal(0);
  readonly loading = signal(false);
  readonly error = signal<string | null>(null);

  readonly filters = this.fb.nonNullable.group({
    entity_type: [''],
    entity_id: [''],
    action: [''],
    from: [''],
    to: [''],
  });

  ngOnInit(): void {
    void this.load();
  }

  async load(): Promise<void> {
    this.loading.set(true);
    this.error.set(null);
    try {
      const value = this.filters.getRawValue();
      const page = await firstValueFrom(
        this.api.get<Page<AuditLog>>('/audit-logs', {
          entity_type: value.entity_type,
          entity_id: value.entity_id.trim(),
          action: value.action,
          from: value.from,
          to: value.to,
          limit: 100,
        }),
      );
      this.logs.set(page.items);
      this.total.set(page.total);
    } catch (error) {
      this.error.set(errorMessage(error));
    } finally {
      this.loading.set(false);
    }
  }

  formatChanges(log: AuditLog): string {
    return JSON.stringify(log.changes, null, 2);
  }
}
