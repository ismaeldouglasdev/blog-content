---
title: "Advanced React Hooks: Essential useEffect, useRef, and Custom Hooks"
date: "2026-08-18"
category: "tutorial"
tags: []
excerpt: "By 2018, 85% of React projects had already adopted Hooks. â State of React Survey 2023"
lang: "en"
translation_of: "2026-08-18-react-hooks-avancados-useeffect,-useref-e-custom-hooks-que-v"
---

---

## Introduction: Why did Hooks change React?

> **“In 2018, 85 % of React projects had already adopted Hooks.”** – State of React Survey 2023  

If you started programming in React before version 16.8, you probably still remember the saga of class components: `componentDidMount`, `componentWillUnmount`, `this.setState`, and the eternal struggle against method binding. It was a period of limited productivity and, let's face it, verbose code.

Then Hooks arrived as a silent revolution. They brought two central promises:

1. **Simple composition of state logic** – no more inheritance hierarchies or complicated "wrapper components".  
2. **Direct access to the lifecycle** – everything within the same function, without needing to create classes.

But, like any powerful tool, Hooks require deep understanding. It's not enough to use `useState` and `useEffect` superficially; to truly harness React's potential, we need to master the advanced hooks: `useEffect` with proper cleanup, `useRef` for persistent values and DOM references, and, of course, creating our own custom hooks that are reusable.

In this article, we'll dive into the details that make a difference in the day-to-day life of a full-stack developer. Get your keyboard ready, open VS Code, and follow along with the real examples you can copy-paste into your projects.

---  

##  useEffect with cleanup and dependencies

### What does `useEffect` really do?

`useEffect` replaces class lifecycle methods (`componentDidMount`, `componentDidUpdate`, `componentWillUnmount`). It accepts two things:

```tsx
useEffect(() => {
  // side-effect
  return () => {
    // cleanup function
  };
}, [/* dependency list */]);
```

- The first argument is the function that will be executed after rendering.  
- The returned value (if any) will be called before the next effect execution or when the component is unmounted.  
- The second argument (dependency array) controls when the effect should be re-executed.

### Example 1 – Fetching data with cancellation

Imagine a component that fetches user details when it mounts. If the user navigates to another page before the request finishes, we need to abort the call to avoid memory leaks and state updates in unmounted components.

```tsx
import { useEffect, useState } from 'react';

function useUser(id: string) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(()