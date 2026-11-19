import { ChangeDetectionStrategy, Component, OnInit, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { firstValueFrom } from 'rxjs';

import { ApiService, errorMessage } from '../../core/api';
import { Dashboard, NotSeenReport } from '../../core/models';

@Component({
  selector: 'app-dashboard-page',
  imports: [RouterLink],
  templateUrl: './dashboard.page.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class DashboardPage implements OnInit {
  private readonly api = inject(ApiService);

  readonly dashboard = signal<Dashboard | null>(null);
  readonly notSeen = signal<NotSeenReport | null>(null);
  readonly loading = signal(false);
  readonly error = signal<string | null>(null);

  ngOnInit(): void {
    void this.load();
  }

  async load(): Promise<void> {
    this.loading.set(true);
    this.error.set(null);
    try {
      const dashboard = await firstValueFrom(
        this.api.get<Dashboard>('/reports/dashboard'),
      );
      this.dashboard.set(dashboard);
      const since = new Date(`${dashboard.today}T00:00:00`);
      since.setDate(since.getDate() - 30);
      const notSeen = await firstValueFrom(
        this.api.get<NotSeenReport>('/reports/not-seen', {
          since: since.toISOString().slice(0, 10),
        }),
      );
      this.notSeen.set(notSeen);
    } catch (error) {
      this.error.set(errorMessage(error));
    } finally {
      this.loading.set(false);
    }
  }
}
