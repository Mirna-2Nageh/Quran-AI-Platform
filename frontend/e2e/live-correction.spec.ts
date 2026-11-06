import { test, expect, type Page } from "@playwright/test";

const api = "";

async function setup(page: Page) {
  await page.route(`${api}/api/v1/auth/me`, route =>
    route.fulfill({ json: {
      id: "e2e-user", email: "e2e@example.test",
      full_name: "E2E User", role: "student",
      created_at: "2026-01-01T00:00:00Z",
    }}),
  );

  await page.route("https://api.alquran.cloud/v1/surah/1/ar.uthmani",
    route => route.fulfill({ json: {
      code: 200,
      data: {
        number: 1, name: "الفاتحة", englishName: "Al-Faatiha",
        numberOfAyahs: 2, revelationType: "Meccan",
        ayahs: [
          { number: 1, numberInSurah: 1, text: "بسم الله الرحمن الرحيم" },
          { number: 2, numberInSurah: 2, text: "الحمد لله رب العالمين" },
        ],
      },
    }}),
  );

  await page.route(`${api}/api/v1/auth/csrf`, route =>
    route.fulfill({
      headers: { "X-CSRF-Token": "e2e-token" },
      json: {},
    }),
  );

  await page.route(`${api}/api/v1/recitation/live-sessions/start`, route =>
    route.fulfill({
      json: { session_id: "e2e-session", status: "active" },
    }),
  );

  await page.route(`${api}/api/v1/recitation/live-sessions/*/finalize`, route =>
    route.fulfill({
      json: {
        session_id: "e2e-session",
        recitation_session_id: "e2e-recitation",
        status: "finalized",
      },
    }),
  );

  await page.route(`${api}/api/v1/recitation/live-correction`, route =>
    route.fulfill({
      json: {
        surah_number: 1,
        ayah_number: 1,
        recognized_text: "بسم الله الرحمن الرحيم",
        alignment: {},
        word_feedback: [],
        next_word_index: 4,
        has_more_words: false,
        analysis_type: "chunk_based_word_alignment",
      },
    }),
  );

  await page.addInitScript(() => {
    const state = { stopped: 0 };
    Object.assign(window, { __micTest: state });

    Object.defineProperty(navigator, "mediaDevices", {
      configurable: true,
      value: {
        getUserMedia: async () => ({
          getTracks: () => [{ stop: () => { state.stopped++; } }],
        }),
      },
    });

    class FakeRecorder {
      state = "inactive";
      onstop: (() => void) | null = null;
      ondataavailable: ((event: { data: Blob }) => void) | null = null;
      onerror: (() => void) | null = null;

      static isTypeSupported() { return true; }

      constructor(...args: unknown[]) { void args; }

      start() {
        Object.assign(window, { __activeRecorder: this });
        this.state = "recording";
        Object.assign(window, { __recorderStarted: true });
      }

      stop() {
        if (this.state !== "recording") return;
        this.state = "inactive";
        Object.assign(window, { __recorderStopped: true });
        this.ondataavailable?.({
          data: new Blob(["fake audio"], { type: "audio/webm" }),
        });
        this.onstop?.();
      }
    }

    Object.assign(window, { MediaRecorder: FakeRecorder });
  });

  await page.goto("/recitation?surah=1&ayah=1");
  await expect(page.getByRole("button", { name: "بدء التسميع" })).toBeVisible();
}

test("start and stop live memorization", async ({ page }) => {
  await setup(page);

  await page.getByRole("button", { name: "بدء التسميع" }).click();
  await expect(page.getByRole("button", { name: "إيقاف التسميع" })).toBeVisible();

  await page.getByRole("button", { name: "إيقاف التسميع" }).click();
  await expect(
    page.getByRole("status").filter({ hasText: "تم حفظ التلاوة بنجاح." })
  ).toBeVisible();

  const stopped = await page.evaluate(
    () => (window as unknown as { __micTest: { stopped: number } })
      .__micTest.stopped,
  );
  expect(stopped).toBeGreaterThan(0);
});

test("changing ayah stops active microphone", async ({ page }) => {
  await setup(page);

  await page.getByRole("button", { name: "بدء التسميع" }).click();
  await expect(page.getByRole("button", { name: "إيقاف التسميع" })).toBeVisible();

  await page.getByLabel("من آية").selectOption("2");

  await expect(page.getByRole("button", { name: "بدء التسميع" })).toBeVisible();

  const stopped = await page.evaluate(
    () => (window as unknown as { __micTest: { stopped: number } })
      .__micTest.stopped,
  );
  expect(stopped).toBeGreaterThan(0);
});

test("live chunk sends correct metadata and displays feedback", async ({ page }) => {
  page.on("request", request => {
    if (request.url().includes("/api/v1/auth/csrf") ||
        request.url().includes("/api/v1/recitation/live-correction")) {
      console.log("API REQUEST:", request.method(), request.url());
    }
  });

  page.on("requestfailed", request => {
    console.log("REQUEST FAILED:", request.url(), request.failure());
  });

  page.on("response", response => {
    if (response.url().includes("/api/v1/auth/csrf")) {
      console.log("CSRF RESPONSE:", response.status(),
        response.headers()["x-csrf-token"] ?? "MISSING");
    }
  });

  page.on("console", message => {
    if (message.type() === "error")
      console.log("BROWSER ERROR:", message.text());
  });
  await setup(page);

  const metadata: Record<string, string> = {};

  await page.route(`${api}/api/v1/auth/csrf`, route =>
    route.fulfill({
      headers: {
        "X-CSRF-Token": "e2e-token",
        "Access-Control-Allow-Origin": "http://127.0.0.1:5173",
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Expose-Headers": "X-CSRF-Token",
        "Access-Control-Allow-Headers": "X-CSRF-Token, Content-Type",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
      },
      json: {},
    }),
  );

  await page.route(`${api}/api/v1/recitation/live-correction`, async route => {
    const cors = {
      "Access-Control-Allow-Origin": "http://127.0.0.1:5173",
      "Access-Control-Allow-Credentials": "true",
      "Access-Control-Allow-Headers": "X-CSRF-Token, Content-Type",
      "Access-Control-Allow-Methods": "POST, OPTIONS",
    };

    if (route.request().method() === "OPTIONS") {
      await route.fulfill({ status: 204, headers: cors });
      return;
    }

    const request = route.request();
    const body = request.postDataBuffer();
    const text = body?.toString("utf8") ?? "";

    for (const key of ["surah_number", "ayah_number", "start_word_index"]) {
      const match = text.match(new RegExp(`name="${key}"\\r\\n\\r\\n([^\\r]+)`));
      metadata[key] = match?.[1] ?? "";
    }

    await route.fulfill({
      headers: cors,
      json: {
        surah_number: 1,
        ayah_number: 1,
        recognized_text: "بسم الله",
        alignment: {},
        word_feedback: [{
          index: 0,
          word: "بسم",
          status: "matched",
          recognized_word: "بسم",
        }],
        next_word_index: 1,
        has_more_words: false,
        analysis_type: "chunk_based_word_alignment",
      },
    });
  });

  await page.getByRole("button", { name: "بدء التسميع" }).click();
  await expect.poll(() =>
    page.evaluate(() =>
      (window as unknown as { __recorderStarted?: boolean })
        .__recorderStarted === true,
    ),
  ).toBe(true);

  await page.evaluate(() => {
    const recorder = (window as unknown as { __activeRecorder?: { stop(): void; state: string } }).__activeRecorder;
    if (!recorder) throw new Error("No active recorder");
    recorder.stop();
  });
  console.log("RECORDER STATE:", await page.evaluate(() => ({
    started: (window as unknown as { __recorderStarted?: boolean }).__recorderStarted,
    stopped: (window as unknown as { __recorderStopped?: boolean }).__recorderStopped,
    activeRecorderState: (window as unknown as { __activeRecorder?: { stop(): void; state: string } }).__activeRecorder?.state,
    recording: document.body.innerText.includes("إيقاف التسميع"),
    errors: [...document.querySelectorAll('[role="alert"]')]
      .map(el => el.textContent),
  })));


  await expect(page.getByRole("heading", { name: "نتيجة التسميع المباشر" }))
    .toBeVisible();

  expect(metadata).toEqual({
    surah_number: "1",
    ayah_number: "1",
    start_word_index: "0",
  });

  await expect(page.locator(".recitation-live-feedback"))
    .toContainText("بسم الله");
});

test("stopping prevents stale feedback", async ({ page }) => {
  page.on("request", request => {
    if (request.url().includes("/api/v1/auth/csrf") ||
        request.url().includes("/api/v1/recitation/live-correction")) {
      console.log("API REQUEST:", request.method(), request.url());
    }
  });

  page.on("requestfailed", request => {
    console.log("REQUEST FAILED:", request.url(), request.failure());
  });

  page.on("response", response => {
    if (response.url().includes("/api/v1/auth/csrf")) {
      console.log("CSRF RESPONSE:", response.status(),
        response.headers()["x-csrf-token"] ?? "MISSING");
    }
  });

  page.on("console", message => {
    if (message.type() === "error")
      console.log("BROWSER ERROR:", message.text());
  });
  await setup(page);

  let releaseResponse: (() => void) | undefined;
  const pending = new Promise<void>(resolve => {
    releaseResponse = resolve;
  });

  await page.route(`${api}/api/v1/auth/csrf`, route =>
    route.fulfill({
      headers: {
        "X-CSRF-Token": "e2e-token",
        "Access-Control-Allow-Origin": "http://127.0.0.1:5173",
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Expose-Headers": "X-CSRF-Token",
        "Access-Control-Allow-Headers": "X-CSRF-Token, Content-Type",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
      },
      json: {},
    }),
  );

  let requestStarted = false;

  await page.route(`${api}/api/v1/recitation/live-correction`, async route => {
    const cors = {
      "Access-Control-Allow-Origin": "http://127.0.0.1:5173",
      "Access-Control-Allow-Credentials": "true",
      "Access-Control-Allow-Headers": "X-CSRF-Token, Content-Type",
      "Access-Control-Allow-Methods": "POST, OPTIONS",
    };

    if (route.request().method() === "OPTIONS") {
      await route.fulfill({ status: 204, headers: cors });
      return;
    }

    requestStarted = true;
    await pending;

    await route.fulfill({
      headers: cors,
      json: {
        surah_number: 1,
        ayah_number: 1,
        recognized_text: "نتيجة قديمة",
        alignment: {},
        word_feedback: [],
        next_word_index: 1,
        has_more_words: false,
        analysis_type: "chunk_based_word_alignment",
      },
    }).catch(() => {});
  });

  await page.getByRole("button", { name: "بدء التسميع" }).click();
  await expect.poll(() =>
    page.evaluate(() =>
      (window as unknown as { __recorderStarted?: boolean })
        .__recorderStarted === true,
    ),
  ).toBe(true);

  await page.evaluate(() => {
    const recorder = (window as unknown as { __activeRecorder?: { stop(): void; state: string } }).__activeRecorder;
    if (!recorder) throw new Error("No active recorder");
    recorder.stop();
  });
  console.log("RECORDER STATE:", await page.evaluate(() => ({
    started: (window as unknown as { __recorderStarted?: boolean }).__recorderStarted,
    stopped: (window as unknown as { __recorderStopped?: boolean }).__recorderStopped,
    activeRecorderState: (window as unknown as { __activeRecorder?: { stop(): void; state: string } }).__activeRecorder?.state,
    recording: document.body.innerText.includes("إيقاف التسميع"),
    errors: [...document.querySelectorAll('[role="alert"]')]
      .map(el => el.textContent),
  })));


  await expect.poll(() => requestStarted).toBe(true);

  await page.getByRole("button", { name: "إيقاف التسميع" }).click();

  releaseResponse?.();

  await expect(page.locator(".recitation-live-feedback")).toHaveCount(0);
});


test("failed chunk retries before finalization", async ({ page }) => {
  let attempts = 0;
  let finalizations = 0;

  await setup(page);

  await page.route(`${api}/api/v1/recitation/live-correction`, async route => {
    attempts += 1;

    if (attempts === 1) {
      await route.fulfill({
        status: 503,
        json: { detail: "Temporary ASR failure" },
      });
      return;
    }

    await route.fulfill({
      json: {
        surah_number: 1,
        ayah_number: 1,
        recognized_text: "بسم الله الرحمن الرحيم",
        alignment: {},
        word_feedback: [],
        next_word_index: 4,
        has_more_words: false,
        analysis_type: "chunk_based_word_alignment",
      },
    });
  });

  await page.route(`${api}/api/v1/recitation/live-sessions/*/finalize`, route => {
    finalizations += 1;
    return route.fulfill({
      json: {
        session_id: "e2e-session",
        recitation_session_id: "e2e-recitation",
        status: "finalized",
      },
    });
  });

  await page.getByRole("button", { name: "بدء التسميع" }).click();
  await expect(page.getByRole("button", { name: "إيقاف التسميع" }))
    .toBeVisible();

  await page.getByRole("button", { name: "إيقاف التسميع" }).click();

  await expect(page.getByRole("button", {
    name: "إعادة محاولة حفظ التلاوة",
  })).toBeVisible();

  expect(attempts).toBe(1);
  expect(finalizations).toBe(0);

  await page.getByRole("button", {
    name: "إعادة محاولة حفظ التلاوة",
  }).click();

  await expect(page.getByRole("status")
    .filter({ hasText: "تم حفظ التلاوة بنجاح." }))
    .toBeVisible();

  expect(attempts).toBe(2);
  expect(finalizations).toBe(1);
});


test("multiple chunks process sequentially before finalization", async ({ page }) => {
  await setup(page);

  const received: Array<{ chunk: number; cursor: number }> = [];
  let inFlight = 0;
  let maxInFlight = 0;
  let finalizations = 0;
  let releaseFirst: (() => void) | undefined;

  const firstBlocked = new Promise<void>(resolve => {
    releaseFirst = resolve;
  });

  await page.route(`${api}/api/v1/recitation/live-correction`, async route => {
    const body = route.request().postDataBuffer()?.toString("utf8") ?? "";

    const field = (name: string) =>
      body.match(new RegExp(`name="${name}"\\r\\n\\r\\n([^\\r]+)`))?.[1] ?? "";

    const chunk = Number(field("chunk_index"));
    const cursor = Number(field("start_word_index"));

    received.push({ chunk, cursor });
    inFlight++;
    maxInFlight = Math.max(maxInFlight, inFlight);

    if (chunk === 0) await firstBlocked;

    await route.fulfill({
      json: {
        surah_number: 1,
        ayah_number: 1,
        recognized_text: "بسم الله الرحمن الرحيم",
        alignment: {},
        word_feedback: [],
        next_word_index: chunk + 1,
        has_more_words: chunk < 2,
        analysis_type: "chunk_based_word_alignment",
      },
    });

    inFlight--;
  });

  await page.route(`${api}/api/v1/recitation/live-sessions/*/finalize`, route => {
    finalizations++;
    return route.fulfill({
      json: {
        session_id: "e2e-session",
        recitation_session_id: "e2e-recitation",
        status: "finalized",
      },
    });
  });

  await page.getByRole("button", { name: "بدء التسميع" }).click();
  await expect(page.getByRole("button", { name: "إيقاف التسميع" }))
    .toBeVisible();

  // Complete the first recording chunk.
  await page.evaluate(() => {
    const recorder = (window as unknown as {
      __activeRecorder?: { stop(): void };
    }).__activeRecorder;
    if (!recorder) throw new Error("No recorder");
    recorder.stop();
  });

  await expect.poll(() => received.length).toBe(1);

  // Complete the second and third chunks while ASR #0 is blocked.
  for (let i = 0; i < 2; i++) {
    await page.evaluate(() => {
      const recorder = (window as unknown as {
        __activeRecorder?: { stop(): void };
      }).__activeRecorder;
      if (!recorder) throw new Error("No recorder");
      recorder.stop();
    });
  }

  expect(received).toEqual([{ chunk: 0, cursor: 0 }]);
  expect(maxInFlight).toBe(1);
  expect(finalizations).toBe(0);

  releaseFirst?.();

  await expect(page.getByRole("status")
    .filter({ hasText: "تم حفظ التلاوة بنجاح." }))
    .toBeVisible({ timeout: 15000 });

  expect(received).toEqual([
    { chunk: 0, cursor: 0 },
    { chunk: 1, cursor: 1 },
    { chunk: 2, cursor: 2 },
  ]);
  expect(maxInFlight).toBe(1);
  expect(finalizations).toBe(1);
});


test("ayah completion stops recording and releases microphone", async ({ page }) => {
  await setup(page);

  let analyses = 0;
  let finalizations = 0;

  await page.route(`${api}/api/v1/recitation/live-correction`, route => {
    analyses++;
    return route.fulfill({
      json: {
        surah_number: 1,
        ayah_number: 1,
        recognized_text: "بسم الله الرحمن الرحيم",
        alignment: {},
        word_feedback: [],
        next_word_index: 4,
        has_more_words: false,
        analysis_type: "chunk_based_word_alignment",
      },
    });
  });

  await page.route(`${api}/api/v1/recitation/live-sessions/*/finalize`, route => {
    finalizations++;
    return route.fulfill({
      json: {
        session_id: "e2e-session",
        recitation_session_id: "e2e-recitation",
        status: "finalized",
      },
    });
  });

  await page.getByRole("button", { name: "بدء التسميع" }).click();
  await expect(page.getByRole("button", { name: "إيقاف التسميع" }))
    .toBeVisible();

  await page.evaluate(() => {
    const recorder = (window as unknown as {
      __activeRecorder?: { stop(): void };
    }).__activeRecorder;
    if (!recorder) throw new Error("No active recorder");
    recorder.stop();
  });

  await expect(page.getByRole("status")
    .filter({ hasText: "تم حفظ التلاوة بنجاح." }))
    .toBeVisible({ timeout: 15000 });

  const state = await page.evaluate(() => ({
    stoppedTracks: (window as unknown as {
      __micTest?: { stopped: number };
    }).__micTest?.stopped ?? 0,
    recorderState: (window as unknown as {
      __activeRecorder?: { state: string };
    }).__activeRecorder?.state,
  }));

  expect(analyses).toBe(1);
  expect(finalizations).toBe(1);
  expect(state.stoppedTracks).toBeGreaterThan(0);
  expect(state.recorderState).toBe("inactive");
});
